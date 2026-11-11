"""Read-only Spotify now-playing integration using OAuth PKCE."""

import base64
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import secrets
import tempfile
import threading
import time
from urllib.parse import urlencode, urlsplit

import requests
from PIL import Image, ImageDraw, BdfFontFile, ImageEnhance, ImageOps

from config import PROJECT_DIR, settings_path


class TickerFont:
    """Draw the ticker's original 5x8 BDF glyphs into clipped Pillow panels."""

    def __init__(self):
        with (PROJECT_DIR / '5x8.bdf').open('rb') as file:
            self.glyphs = BdfFontFile.BdfFontFile(file).glyph

    def glyph(self, character):
        code = ord(character)
        return (self.glyphs[code] if code < len(self.glyphs) else None) or self.glyphs[ord('?')]

    def width(self, text):
        return sum(self.glyph(character)[0][0] for character in text)

    def draw(self, image, x, baseline, color, text):
        for character in text:
            advance, box, _, mask = self.glyph(character)
            image.paste(color, (x + box[0], baseline + box[1],
                                x + box[2], baseline + box[3]), mask)
            x += advance[0]


class SpotifyError(Exception):
    """A message that is safe to show without leaking tokens or request URLs."""


def sample_album_art(image, size, *, preserve_aspect=True):
    """Return RGB album art sampled to an int square or (width, height).

    LANCZOS averages the source pixels for small LED displays. Letterboxing
    preserves the complete cover and its aspect ratio without stretching it.
    Set preserve_aspect=False to fill a rectangular size exactly.
    The source image is never modified.
    """
    if isinstance(size, int):
        size = (size, size)
    if len(size) != 2 or any(type(value) is not int or value < 1 for value in size):
        raise ValueError('Album art size must contain two positive integers.')
    if not preserve_aspect:
        return image.convert('RGB').resize(tuple(size), Image.Resampling.LANCZOS)
    return ImageOps.pad(image.convert('RGB'), tuple(size), method=Image.Resampling.LANCZOS,
                        color=(0, 0, 0))


class Spotify:
    def __init__(self):
        self.client_id = os.getenv('SPOTIFY_CLIENT_ID', '').strip()
        self.redirect_uri = os.getenv(
            'SPOTIFY_REDIRECT_URI', 'http://127.0.0.1:5000/spotify/callback')
        self.cache_path = settings_path().resolve().parent / '.spotify-tokens.json'
        self.lock = threading.Lock()
        self.io_lock = threading.Lock()
        self.tokens = {}
        self.pending = {}
        self.enabled = True
        self.mode = 'ticker'
        self.up_next = False
        self.next_track = None
        self.next_for_track = None
        self.queue_updated = 0
        self.queue_retry_at = 0
        self.queue_error = None
        self.album_art = None
        self.album_url = None
        self.art_samples = {}
        self.track = None
        self.updated = 0
        self.error = None
        self.worker = None
        self.scroll = 0
        self.last_title = None
        self.font = None
        try:
            cache = json.loads(self.cache_path.read_text(encoding='utf-8'))
            if cache.get('client_id') == self.client_id:
                self.tokens = cache.get('tokens', {})
        except (OSError, ValueError, AttributeError):
            pass

    @property
    def configured(self):
        try:
            uri = urlsplit(self.redirect_uri)
            return bool(self.client_id and uri.path == '/spotify/callback' and
                        (uri.scheme == 'https' or
                         (uri.scheme == 'http' and uri.hostname in ('127.0.0.1', '::1')))
                        and not uri.query and not uri.fragment and not uri.username)
        except ValueError:
            return False

    def snapshot(self):
        with self.lock:
            track = dict(self.track) if self.track else None
            age = time.monotonic() - self.updated
            # Do not leave stale music on the board after an outage.
            if track and age > 30:
                track['is_playing'] = False
            if track and track['is_playing']:
                track['progress_ms'] = min(track['duration_ms'],
                    track['progress_ms'] + int(age * 1000))
            return dict(configured=self.configured, connected=bool(self.tokens.get('refresh_token')),
                        enabled=self.enabled, mode=self.mode, track=track, error=self.error,
                        upNext=self.up_next, queueError=self.queue_error,
                        nextTrack=dict(self.next_track) if self.next_track and track and
                        self.next_for_track == track['id'] and
                        time.monotonic() - self.queue_updated < 30 else None,
                        album_art_ready=self.album_art is not None and bool(track) and
                        self.album_url == track.get('album_art_url'))

    def ticker_text(self):
        state = self.snapshot()
        track = state['track']
        if not state['enabled'] or not track or not track['is_playing']:
            return None
        if state['mode'] == 'weather':
            next_track = state['nextTrack']
            if state['upNext'] and next_track:
                return f"🎵 Up Next: {next_track['title']} - {next_track['artist']}"
            return None
        if state['mode'] != 'focus' or not state['album_art_ready']:
            return f"🎵 Now Play: {track['title']} - {track['artist']}"
        return None

    def _poll_queue(self, track):
        """Refresh optional Up Next independently of playback/artwork failures."""
        with self.lock:
            requested = self.enabled and self.mode == 'weather' and self.up_next
            if not requested or not track or not track['is_playing']:
                self.next_track, self.queue_error = None, None
                return
            if time.monotonic() < self.queue_retry_at:
                return
        if 'user-read-playback-state' not in self.tokens.get('scope', '').split():
            with self.lock:
                self.next_track = None
                self.queue_error = 'Reconnect Spotify with Up Next enabled to grant queue access.'
            return
        error = None
        next_track = None
        delay = 0
        try:
            response = requests.get('https://api.spotify.com/v1/me/player/queue',
                headers={'Authorization': 'Bearer ' + self.tokens['access_token']}, timeout=10)
            if response.status_code == 200:
                queue = response.json().get('queue') or []
                item = queue[0] if queue else None
                if isinstance(item, dict) and item.get('type') == 'track':
                    next_track = dict(title=item.get('name', ''), artist=', '.join(
                        artist.get('name', '') for artist in item.get('artists', [])))
            elif response.status_code == 429:
                delay = max(5, float(response.headers.get('Retry-After', '30')))
                error = 'Spotify queue rate limit reached. Retrying automatically.'
            elif response.status_code == 403:
                delay = 30
                error = 'Queue access denied. Reconnect Spotify with Up Next enabled and check app access.'
            elif response.status_code == 401:
                self.tokens['expires_at'] = 0
                error = 'Refreshing Spotify queue authorization.'
            else:
                delay = 30
                error = 'Could not load Up Next. Retrying automatically.'
        except (requests.RequestException, ValueError):
            delay = 30
            error = 'Could not load Up Next. Retrying automatically.'
        with self.lock:
            self.next_track = next_track
            self.next_for_track = track['id']
            self.queue_updated = time.monotonic()
            self.queue_retry_at = time.monotonic() + delay
            self.queue_error = error

    def _load_album_art(self, url):
        with self.lock:
            if url == self.album_url and self.album_art is not None:
                return
            self.album_url, self.album_art = url, None
            self.art_samples = {}
        if not url:
            return
        parsed = urlsplit(url)
        host = parsed.hostname or ''
        if parsed.scheme != 'https' or not (host.endswith('.scdn.co') or host.endswith('.spotifycdn.com')):
            return
        # Album downloads run only on the polling thread, without the API bearer token.
        with requests.get(url, timeout=10, stream=True, allow_redirects=False) as response:
            response.raise_for_status()
            chunks, length = [], 0
            for chunk in response.iter_content(65536):
                length += len(chunk)
                if length > 4 * 1024 * 1024:
                    raise ValueError('Album image is too large.')
                chunks.append(chunk)
        with Image.open(BytesIO(b''.join(chunks))) as source:
            art = source.convert('RGB')
        with self.lock:
            self.album_art = art
            self.art_samples = {}

    def authorize(self):
        if not self.configured:
            raise SpotifyError('Set SPOTIFY_CLIENT_ID and a valid SPOTIFY_REDIRECT_URI in settings.toml first.')
        state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        with self.lock:
            self.pending = {key: value for key, value in self.pending.items()
                            if time.monotonic() - value[1] < 600}
            self.pending[state] = (verifier, time.monotonic())
        return state, 'https://accounts.spotify.com/authorize?' + urlencode(dict(
            client_id=self.client_id, response_type='code', redirect_uri=self.redirect_uri,
            scope='user-read-currently-playing' + (' user-read-playback-state' if self.up_next else ''), state=state,
            code_challenge_method='S256', code_challenge=challenge))

    def complete(self, code, state, cookie):
        if not state or not cookie or not secrets.compare_digest(state, cookie):
            raise SpotifyError('Sign-in expired or did not start in this browser. Connect again.')
        with self.lock:
            pending = self.pending.pop(state, None)
        if not code or not pending or time.monotonic() - pending[1] > 600:
            raise SpotifyError('Sign-in expired or was cancelled. Connect again.')
        with self.io_lock:
            self._token_request(dict(grant_type='authorization_code', code=code,
                                     redirect_uri=self.redirect_uri, code_verifier=pending[0]))
        with self.lock:
            self.error = None

    def _token_request(self, data):
        response = requests.post('https://accounts.spotify.com/api/token',
                                 data=dict(data, client_id=self.client_id), timeout=10)
        if response.status_code != 200:
            if response.status_code in (400, 401):
                with self.lock:
                    self.tokens = {}
                self.cache_path.unlink(missing_ok=True)
            raise SpotifyError('Spotify sign-in needs attention. Connect your account again.')
        token = response.json()
        if not token.get('access_token'):
            raise SpotifyError('Spotify returned an invalid sign-in response. Connect again.')
        with self.lock:
            tokens = dict(self.tokens, **token, expires_at=time.time() + token.get('expires_in', 3600))
        # Persist refresh tokens atomically; never include them in API snapshots.
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                    dir=self.cache_path.parent, prefix='.spotify-', suffix='.tmp', delete=False) as file:
                temporary = Path(file.name)
                os.chmod(temporary, 0o600)
                json.dump(dict(client_id=self.client_id, tokens=tokens), file)
            os.replace(temporary, self.cache_path)
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)
        with self.lock:
            self.tokens = tokens

    def disconnect(self):
        with self.io_lock:
            self.cache_path.unlink(missing_ok=True)
            with self.lock:
                self.tokens = {}
                self.track = None
                self.next_track = None
                self.queue_error = None
                self.queue_retry_at = 0
                self.album_art = None
                self.album_url = None
                self.art_samples = {}
                self.error = None
                self.pending.clear()

    def poll(self):
        """Return seconds until the next request, respecting Spotify rate limits."""
        with self.io_lock:
            if not self.configured or not self.tokens.get('refresh_token'):
                return 5
            if self.tokens.get('expires_at', 0) < time.time() + 60:
                self._token_request(dict(grant_type='refresh_token', refresh_token=self.tokens['refresh_token']))
            response = requests.get('https://api.spotify.com/v1/me/player/currently-playing',
                headers={'Authorization': 'Bearer ' + self.tokens['access_token']}, timeout=10)
            if response.status_code == 401:
                self._token_request(dict(grant_type='refresh_token', refresh_token=self.tokens['refresh_token']))
                return 5
            if response.status_code == 429:
                with self.lock:
                    self.error = 'Spotify rate limit reached. Retrying automatically.'
                try:
                    return max(5, float(response.headers.get('Retry-After', '30')))
                except ValueError:
                    return 30
            if response.status_code == 403:
                raise SpotifyError('Spotify denied access. Check your app users and account eligibility in the Developer Dashboard.')
            if response.status_code not in (200, 204):
                raise SpotifyError('Spotify is unavailable. Retrying automatically.')
            data = response.json() if response.status_code == 200 else {}
            item = data.get('item') or {}
            track = None
            if item and data.get('currently_playing_type') == 'track':
                release_date = item.get('album', {}).get('release_date') or ''
                release_year = release_date[:4] if release_date[:4].isdigit() and len(release_date) >= 4 else ''
                images = item.get('album', {}).get('images', [])
                image = min(images, key=lambda image: abs((image.get('width') or 300) - 300)) if images else {}
                track = dict(id=item.get('id') or item.get('uri'), title=item.get('name', ''),
                    artist=', '.join(artist.get('name', '') for artist in item.get('artists', [])),
                    is_playing=bool(data.get('is_playing')), progress_ms=data.get('progress_ms') or 0,
                    duration_ms=item.get('duration_ms') or 0, album_art_url=image.get('url'),
                    release_year=release_year)
            art_error = None
            try:
                self._load_album_art(track.get('album_art_url') if track else None)
            except (requests.RequestException, ValueError, OSError, Image.DecompressionBombError):
                art_error = 'Album art unavailable. Retrying automatically.'
            with self.lock:
                self.track, self.updated, self.error = track, time.monotonic(), art_error
            self._poll_queue(track)
            return 5

    def start(self):
        if self.worker is not None:
            return
        def run():
            while True:
                delay = 5
                try:
                    delay = self.poll()
                except (requests.RequestException, ValueError, OSError, SpotifyError) as error:
                    with self.lock:
                        self.error = str(error) if isinstance(error, SpotifyError) else 'Could not refresh Spotify. Retrying automatically.'
                    delay = 30
                time.sleep(delay)
        self.worker = threading.Thread(target=run, daemon=True, name='spotify-poll')
        self.worker.start()

    def render(self, canvas, dt, brightness):
        state = self.snapshot()
        track = state['track']
        if not state['enabled'] or state['mode'] == 'ticker' or not track or not track['is_playing']:
            return False
        with self.lock:
            if self.album_art is None or self.album_url != track.get('album_art_url'):
                return False
            art_size = 20 if state['mode'] == 'weather' else 24
            if art_size not in self.art_samples:
                self.art_samples[art_size] = sample_album_art(
                    self.album_art, art_size, preserve_aspect=state['mode'] != 'weather')
            art = self.art_samples[art_size]
        key = (track['id'], track['title'], track['artist'], state['mode'])
        self.scroll = self.scroll + max(0, dt) * 18 if key == self.last_title else 0
        self.last_title = key
        if state['mode'] == 'weather':
            return self.render_weather(canvas, track, art, brightness)
        return self.render_focus(canvas, track, art, brightness)

    def render_weather(self, canvas, track, art, brightness):
        """Replace only the weather area, keeping the clock and ticker visible."""
        image = self._render_panel(track, art, brightness, canvas.width - 58, 24,
                                   title_y=7, artist_y=17)
        canvas.SetImage(image, 58, 0)
        return True

    def render_focus(self, canvas, track, art, brightness):
        """Fill the board with album art, song details, and playback progress."""
        image = self._render_panel(track, art, brightness, canvas.width, canvas.height,
                                   title_y=7, artist_y=17)
        metadata_color = tuple(round(value * max(0, min(1, brightness)))
                               for value in (170, 190, 180))
        text_x = art.width + (canvas.height - art.height)
        self.font.draw(image, text_x, 27, metadata_color, track.get('release_year', ''))
        seconds = max(0, track['duration_ms']) // 1000
        duration = f'{seconds // 60}:{seconds % 60:02d}'
        self.font.draw(image, canvas.width - self.font.width(duration), 27,
                       metadata_color, duration)
        canvas.Clear()
        canvas.SetImage(image, 0, 0)
        return True

    def _render_panel(self, track, art, brightness, width, height, *,
                      title_y, artist_y):
        """Compose shared album art, scrolling text, and the progress bar."""
        image = Image.new('RGB', (width, height))
        padding = (height - art.height) // 2
        image.paste(ImageEnhance.Brightness(art).enhance(max(0, min(1, brightness))),
                    (padding, padding))
        text_x = art.width + padding * 2
        text_width_available = width - text_x
        text_image = Image.new('RGB', (max(1, text_width_available), height))
        draw = ImageDraw.Draw(text_image)
        if self.font is None:
            self.font = TickerFont()
        def color(rgb):
            return tuple(round(value * max(0, min(1, brightness))) for value in rgb)
        for text, row_y, rgb in ((track['title'], title_y, (255, 255, 255)),
                             (track['artist'], artist_y, (170, 190, 180))):
            text = text.encode('latin-1', 'replace').decode('latin-1')
            text_width = self.font.width(text)
            offset = int(self.scroll % (text_width + 24)) if text_width > text_width_available else 0
            self.font.draw(text_image, -offset, row_y, color(rgb), text)
            if text_width > text_width_available:
                self.font.draw(text_image, text_width + 24 - offset, row_y, color(rgb), text)
        draw.line((0, height - 1, text_width_available - 1, height - 1), fill=color((25, 40, 30)))
        progress = track['progress_ms'] / max(1, track['duration_ms'])
        if progress > 0:
            draw.line((0, height - 1, min(text_width_available - 1, int(text_width_available * progress)), height - 1),
                      fill=color((30, 215, 96)))
        image.paste(text_image, (text_x, 0))
        return image
