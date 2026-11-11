import ast
import asyncio
import base64
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
from io import BytesIO
import unittest
from unittest.mock import AsyncMock, Mock, patch
from urllib.parse import parse_qs, urlsplit

from PIL import Image

from spotify import Spotify, SpotifyError, sample_album_art
from ser import ser
from tickertape import TickerTapeManager, ticktape


class SpotifyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.env = patch.dict(os.environ, {
            'SPOTIFY_CLIENT_ID': 'test-client',
            'SPOTIFY_REDIRECT_URI': 'http://127.0.0.1:5000/spotify/callback',
            'LED_SETTINGS_FILE': str(Path(self.directory.name) / 'settings.toml'),
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.spotify = Spotify()

    def connect(self):
        self.spotify.tokens = dict(access_token='private-access', refresh_token='private-refresh',
                                   expires_at=time.time() + 3600)

    def track_response(self, playing=True):
        return Mock(status_code=200, json=lambda: dict(is_playing=playing,
            currently_playing_type='track', progress_ms=1000,
            item=dict(id='song', name='Test song', duration_ms=180000,
                      album=dict(release_date='2024-06-14'),
                      artists=[dict(name='Artist A'), dict(name='Artist B')])))

    def test_pkce_callback_requires_browser_state_and_persists_tokens(self):
        state, url = self.spotify.authorize()
        query = parse_qs(urlsplit(url).query)
        verifier = self.spotify.pending[state][0]
        expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        self.assertEqual(query['code_challenge'], [expected])
        self.assertEqual(query['scope'], ['user-read-currently-playing'])
        with patch('spotify.requests.post') as post:
            with self.assertRaises(SpotifyError):
                self.spotify.complete('code', state, 'other-browser')
            post.assert_not_called()
            post.return_value = Mock(status_code=200, json=lambda: dict(
                access_token='private-access', refresh_token='private-refresh', expires_in=3600))
            self.spotify.complete('code', state, state)
            self.assertEqual(post.call_args.kwargs['data']['code_verifier'], verifier)
            with self.assertRaises(SpotifyError):
                self.spotify.complete('code', state, state)
        reloaded = Spotify()
        self.assertTrue(reloaded.snapshot()['connected'])
        self.assertNotIn('private-', json.dumps(reloaded.snapshot()))
        self.assertFalse(list(Path(self.directory.name).glob('*.tmp')))

    def test_expired_state_and_invalid_redirect_are_rejected(self):
        state, _ = self.spotify.authorize()
        verifier, _ = self.spotify.pending[state]
        self.spotify.pending[state] = (verifier, time.monotonic() - 601)
        with self.assertRaises(SpotifyError):
            self.spotify.complete('code', state, state)
        for uri in ('http://localhost:5000/spotify/callback',
                    'http://192.168.1.20:5000/spotify/callback'):
            self.spotify.redirect_uri = uri
            self.assertFalse(self.spotify.configured)

    def test_refresh_retains_refresh_token_and_uses_new_access_token(self):
        self.connect()
        self.spotify.tokens['expires_at'] = 0
        with patch('spotify.requests.post', return_value=Mock(status_code=200,
                json=lambda: dict(access_token='new-access', expires_in=3600))) as post, \
             patch('spotify.requests.get', return_value=self.track_response()) as get:
            self.assertEqual(self.spotify.poll(), 5)
        self.assertEqual(post.call_args.kwargs['data']['grant_type'], 'refresh_token')
        self.assertEqual(get.call_args.kwargs['headers']['Authorization'], 'Bearer new-access')
        self.assertEqual(self.spotify.tokens['refresh_token'], 'private-refresh')
        self.assertEqual(self.spotify.snapshot()['track']['artist'], 'Artist A, Artist B')

    def test_idle_paused_and_non_music_do_not_render(self):
        self.connect()
        canvas = Mock(width=128, height=32)
        responses = [Mock(status_code=204), self.track_response(False),
                     Mock(status_code=200, json=lambda: dict(
                         currently_playing_type='episode', is_playing=True, item=dict(name='Podcast')))]
        for response in responses:
            with patch('spotify.requests.get', return_value=response):
                self.spotify.poll()
            self.assertFalse(self.spotify.render(canvas, .016, 1))
        canvas.SetImage.assert_not_called()

    def test_rate_limits_and_stale_playback(self):
        self.connect()
        with patch('spotify.requests.get', return_value=self.track_response()):
            self.spotify.poll()
        with patch('spotify.requests.get', return_value=Mock(status_code=429,
                headers={'Retry-After': '120'})):
            self.assertEqual(self.spotify.poll(), 120)
        self.spotify.updated -= 31
        self.assertFalse(self.spotify.snapshot()['track']['is_playing'])
        self.assertFalse(self.spotify.render(Mock(), .016, 1))

    def test_unauthorized_refreshes_and_revoked_tokens_disconnect(self):
        self.connect()
        with patch('spotify.requests.get', return_value=Mock(status_code=401)), \
             patch('spotify.requests.post', return_value=Mock(status_code=200,
                   json=lambda: dict(access_token='replacement', expires_in=3600))):
            self.spotify.poll()
        self.assertEqual(self.spotify.tokens['access_token'], 'replacement')
        self.spotify.tokens['expires_at'] = 0
        with patch('spotify.requests.post', return_value=Mock(status_code=400)):
            with self.assertRaises(SpotifyError):
                self.spotify.poll()
        self.assertFalse(self.spotify.snapshot()['connected'])
        self.assertFalse(self.spotify.cache_path.exists())

    def test_render_scrolling_progress_and_brightness(self):
        self.connect()
        with patch('spotify.requests.get', return_value=self.track_response()):
            self.spotify.poll()
        self.spotify.track['title'] = 'A long title that needs scrolling on the display'
        self.spotify.mode = 'focus'
        self.spotify.album_art = Image.new('RGB', (300, 300), (200, 40, 20))
        canvas = Mock(width=128, height=32)
        self.assertTrue(self.spotify.render(canvas, .016, 1))
        image = canvas.SetImage.call_args.args[0]
        self.assertEqual(image.size, (128, 32))
        self.assertEqual(image.getpixel((0, 31)), (0, 0, 0))
        self.assertEqual(image.getpixel((4, 4)), (200, 40, 20))
        self.assertGreater(sum(image.getpixel((34, 31))), 0)
        self.assertEqual(self.spotify.snapshot()['track']['release_year'], '2024')
        metadata = Image.new('RGB', (96, 9))
        self.spotify.font.draw(metadata, 0, 7, (170, 190, 180), '2024')
        self.spotify.font.draw(metadata, 96 - self.spotify.font.width('3:00'), 7,
                               (170, 190, 180), '3:00')
        self.assertEqual(image.crop((32, 20, 128, 29)).tobytes(), metadata.tobytes())
        self.assertTrue(self.spotify.render(canvas, 1, 0))
        self.assertIsNone(canvas.SetImage.call_args.args[0].getbbox())
        self.assertEqual(self.spotify.scroll, 18)
        self.spotify.enabled = False
        self.assertFalse(self.spotify.render(canvas, .016, 1))

    def test_disconnect_removes_cache_and_saved_account(self):
        self.connect()
        self.spotify.cache_path.write_text('secret')
        self.spotify.disconnect()
        self.assertFalse(self.spotify.cache_path.exists())
        self.assertFalse(self.spotify.snapshot()['connected'])
        self.assertIsNone(self.spotify.snapshot()['track'])

    def test_routes_validate_callback_and_never_expose_tokens(self):
        server = ser()
        client = server.app.test_client()
        for value in (None, 1, 'true', [], {}):
            self.assertEqual(client.post('/spotify', json=dict(enabled=value)).status_code, 400)
        self.assertFalse(client.post('/spotify', json=dict(enabled=False)).json['enabled'])
        self.assertEqual(client.get('/spotify').headers['Cache-Control'], 'no-store')
        self.assertEqual(client.get('/spotify/callback?code=bad&state=wrong').status_code, 400)
        response = client.get('/spotify/connect')
        state = parse_qs(urlsplit(response.location).query)['state'][0]
        self.assertIn('HttpOnly', response.headers['Set-Cookie'])
        with patch('spotify.requests.post', return_value=Mock(status_code=200,
                json=lambda: dict(access_token='private-access', refresh_token='private-refresh'))):
            self.assertEqual(client.get('/spotify/callback', query_string=dict(code='code', state=state)).status_code, 302)
        self.assertNotIn('private-', client.get('/spotify').get_data(as_text=True))
        self.assertFalse(client.post('/spotify/disconnect', json={}).json['connected'])

    def test_display_restores_normal_content_when_music_stops(self):
        tree = ast.parse((Path(__file__).resolve().parents[1] / 'main.py').read_text())
        main = next(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef)
                    and node.name == 'main')
        server = Mock()
        server.getFishMode.return_value = False
        server.getSlider.return_value = .5
        server.renderSpotify.side_effect = [True, True, False]
        clock, weather, ticker = Mock(), Mock(), Mock()
        clock.newHour.return_value = False
        weather.location = server.getWeatherLocation.return_value
        weather.refreshInfo = AsyncMock()
        ticker.refreshInfo = AsyncMock()
        for element in (clock, weather, ticker):
            element.changed.return_value = False
        namespace = dict(asyncio=asyncio, time=time, threading=Mock(), ser=lambda: server,
            ClockFace=lambda *args: clock, weatherManager=lambda *args: weather,
            TickerTapeManager=lambda *args: ticker, Aquarium=Mock())
        exec(compile(ast.Module(body=[main], type_ignores=[]), 'main.py', 'exec'), namespace)
        canvas = Mock(width=128, height=32)
        matrix = Mock()
        class EndFrames(Exception):
            pass
        matrix.SwapOnVSync.side_effect = [canvas, canvas, EndFrames()]
        with self.assertRaises(EndFrames):
            asyncio.run(namespace['main'](matrix, canvas))
        self.assertEqual(server.renderSpotify.call_count, 3)
        # Base content clears any previous overlay, including when playback stops.
        self.assertEqual(canvas.Clear.call_count, 3)
        for element in (clock, weather, ticker):
            self.assertEqual(element.render.call_count, 3)

    def test_modes_default_to_ticker_and_require_real_art_for_overlays(self):
        self.connect()
        with patch('spotify.requests.get', return_value=self.track_response()):
            self.spotify.poll()
        self.assertEqual(self.spotify.snapshot()['mode'], 'ticker')
        expected = '🎵 Now Play: Test song - Artist A, Artist B'
        self.assertEqual(self.spotify.ticker_text(), expected)
        canvas = Mock(width=128, height=32)
        self.assertFalse(self.spotify.render(canvas, .1, 1))
        for mode in ('weather', 'focus'):
            self.spotify.mode = mode
            self.assertFalse(self.spotify.render(canvas, .1, 1))
            self.assertEqual(self.spotify.ticker_text(), None if mode == 'weather' else expected)
        self.spotify.album_art = Image.new('RGB', (100, 100), (200, 40, 20))
        self.spotify.mode = 'weather'
        self.assertTrue(self.spotify.render(canvas, .1, .5))
        canvas.Clear.assert_not_called()
        image, x, y = canvas.SetImage.call_args.args
        self.assertEqual((x, y, image.size), (58, 0, (70, 24)))
        self.assertEqual(image.getpixel((0, 0)), (0, 0, 0))
        self.assertEqual(image.getpixel((2, 2)), (100, 20, 10))
        self.assertIn(20, self.spotify.art_samples)
        self.assertEqual(self.spotify.art_samples[20].size, (20, 20))
        self.assertEqual(image.getpixel((21, 21)), (100, 20, 10))
        self.assertEqual(image.getpixel((22, 21)), (0, 0, 0))
        self.spotify.mode = 'focus'
        self.assertIsNone(self.spotify.ticker_text())
        self.assertTrue(self.spotify.render(canvas, .1, 1))
        self.assertIn(24, self.spotify.art_samples)
        self.spotify.updated -= 31
        self.assertIsNone(self.spotify.ticker_text())
        self.assertFalse(self.spotify.render(canvas, .1, 1))

    def test_album_sampling_preserves_cover_and_supports_multiple_sizes(self):
        source = Image.new('RGB', (100, 50), (100, 200, 50))
        for size in (16, 24, 32, (60, 24)):
            sampled = sample_album_art(source, size)
            self.assertEqual(sampled.size, (size, size) if isinstance(size, int) else size)
            self.assertEqual(sampled.mode, 'RGB')
            self.assertEqual(sampled.getpixel((sampled.width // 2, sampled.height // 2)), (100, 200, 50))
        self.assertEqual(sample_album_art(source, 24).getpixel((0, 0)), (0, 0, 0))
        self.assertEqual(source.size, (100, 50))
        for size in (0, -1, (1, 0), (1.5, 20)):
            with self.assertRaises(ValueError):
                sample_album_art(source, size)

    def test_album_download_caches_cover_and_discards_previous_album(self):
        buffer = BytesIO()
        Image.new('RGB', (64, 64), (200, 40, 20)).save(buffer, format='PNG')
        response = Mock()
        response.iter_content.return_value = [buffer.getvalue()]
        context = Mock()
        context.__enter__ = Mock(return_value=response)
        context.__exit__ = Mock(return_value=False)
        url = 'https://i.scdn.co/image/test-cover'
        with patch('spotify.requests.get', return_value=context) as get:
            self.spotify._load_album_art(url)
            self.spotify._load_album_art(url)
            get.assert_called_once()
            self.assertNotIn('headers', get.call_args.kwargs)
        self.assertEqual(self.spotify.album_art.getpixel((0, 0)), (200, 40, 20))
        self.spotify._load_album_art(None)
        self.assertIsNone(self.spotify.album_art)

    def test_modes_api_rejects_invalid_mode_without_changing_other_settings(self):
        server = ser()
        client = server.app.test_client()
        self.assertEqual(client.get('/spotify').json['mode'], 'ticker')
        for mode in ('weather', 'focus', 'ticker'):
            response = client.post('/spotify', json=dict(mode=mode))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['mode'], mode)
        for mode in ('invalid', None, [], 1):
            self.assertEqual(client.post('/spotify', json=dict(mode=mode, enabled=False)).status_code, 400)
            self.assertTrue(server.spotify.enabled)

    def test_green_music_entries_mix_with_news_and_clear_on_pause(self):
        canvas = Mock(width=128, height=32)
        ticker = TickerTapeManager(canvas)
        ticker.newsJson = {'articles': [{'title': 'First news'}, {'title': 'Second news'}]}
        ticker.setBrightness(.5)
        text = '🎵 Now Play: Song - Artist'
        ticker.setNowPlaying(text)
        music = [words for words in ticker.queque if words.kind == 'spotify']
        self.assertEqual(len(music), 1)
        self.assertEqual(music[0].text.strip(), text)
        self.assertEqual((music[0].textColorRaw.red, music[0].textColorRaw.green,
                          music[0].textColorRaw.blue), (30, 215, 96))
        first = ticker.getNextInfo()
        second = ticker.getNextInfo()
        self.assertIn(first.strip(), ('First news', 'Second news'))
        self.assertEqual(second.strip(), text)
        ticker.setNowPlaying('🎵 Now Play: New Song - Artist')
        self.assertFalse(any('Song - Artist' in words.text and 'New Song' not in words.text
                             for words in ticker.queque))
        for previous, following in zip(ticker.queque, ticker.queque[1:]):
            self.assertGreaterEqual(following.x, previous.x + previous.getWidth())
        ticker.setNowPlaying(None)
        self.assertFalse(any(words.kind == 'spotify' for words in ticker.queque))
        for _ in range(5):
            self.assertNotIn('Now Play:', ticker.getNextInfo())

    def test_music_note_renders_even_without_an_emoji_font(self):
        canvas = Mock(width=128, height=32)
        words = ticktape(0, 32, canvas)
        words.setText('🎵 Now Play: Song - Artist')
        words.setTTColor(__import__('tickertape').graphics.Color(30, 215, 96))
        with patch('tickertape.graphics.DrawText') as draw:
            words.render(canvas)
        self.assertGreater(canvas.SetPixel.call_count, 0)
        self.assertEqual(draw.call_args.args[-1], 'Now Play: Song - Artist')

    def enable_up_next(self):
        self.connect()
        self.spotify.mode = 'weather'
        self.spotify.up_next = True
        self.spotify.tokens['scope'] = 'user-read-currently-playing user-read-playback-state'

    def queue_response(self, items=None):
        if items is None:
            items = [dict(type='track', name='Next song', artists=[dict(name='Next artist')])]
        return Mock(status_code=200, json=lambda: dict(queue=items))

    def test_up_next_replaces_now_playing_only_in_weather_ticker(self):
        self.enable_up_next()
        with patch('spotify.requests.get', side_effect=[self.track_response(), self.queue_response()]) as get:
            self.spotify.poll()
        self.assertEqual(get.call_args_list[1].args[0], 'https://api.spotify.com/v1/me/player/queue')
        self.assertEqual(self.spotify.ticker_text(), '🎵 Up Next: Next song - Next artist')
        self.spotify.up_next = False
        self.assertIsNone(self.spotify.ticker_text())
        self.spotify.mode = 'ticker'
        self.assertEqual(self.spotify.ticker_text(), '🎵 Now Play: Test song - Artist A, Artist B')
        self.spotify.mode = 'weather'
        self.spotify.up_next = True
        self.spotify.updated -= 31
        self.assertIsNone(self.spotify.ticker_text())

    def test_up_next_off_does_not_request_queue(self):
        self.connect()
        self.spotify.mode = 'weather'
        with patch('spotify.requests.get', return_value=self.track_response()) as get:
            self.spotify.poll()
        get.assert_called_once()
        self.assertIsNone(self.spotify.ticker_text())

    def test_empty_or_non_music_queue_and_paused_playback_clear_up_next(self):
        self.enable_up_next()
        for items in ([], [dict(type='episode', name='Podcast')]):
            with patch('spotify.requests.get', side_effect=[self.track_response(), self.queue_response(items)]):
                self.spotify.poll()
            self.assertIsNone(self.spotify.ticker_text())
        with patch('spotify.requests.get', side_effect=[self.track_response(), self.queue_response()]):
            self.spotify.poll()
        self.assertIsNotNone(self.spotify.ticker_text())
        with patch('spotify.requests.get', return_value=self.track_response(False)) as get:
            self.spotify.poll()
        get.assert_called_once()
        self.assertIsNone(self.spotify.next_track)
        self.assertIsNone(self.spotify.ticker_text())

    def test_queue_rate_limits_do_not_stop_current_playback_polling(self):
        self.enable_up_next()
        with patch('spotify.requests.get', side_effect=[self.track_response(),
                Mock(status_code=429, headers={'Retry-After': '120'})]):
            self.assertEqual(self.spotify.poll(), 5)
        self.assertTrue(self.spotify.snapshot()['track']['is_playing'])
        self.assertIsNotNone(self.spotify.snapshot()['queueError'])
        self.assertIsNone(self.spotify.ticker_text())
        with patch('spotify.requests.get', return_value=self.track_response()) as get:
            self.spotify.poll()
        get.assert_called_once()

    def test_queue_scope_is_optional_and_existing_connections_need_reconnect(self):
        self.enable_up_next()
        self.spotify.tokens.pop('scope')
        with patch('spotify.requests.get', return_value=self.track_response()) as get:
            self.spotify.poll()
        get.assert_called_once()
        self.assertIn('Reconnect', self.spotify.snapshot()['queueError'])
        _, url = self.spotify.authorize()
        self.assertIn('user-read-playback-state', parse_qs(urlsplit(url).query)['scope'][0].split())
        self.spotify.up_next = False
        _, url = self.spotify.authorize()
        self.assertNotIn('user-read-playback-state', parse_qs(urlsplit(url).query)['scope'][0].split())

    def test_up_next_api_validates_boolean_without_partially_applying_changes(self):
        server = ser()
        client = server.app.test_client()
        self.assertFalse(client.get('/spotify').json['upNext'])
        self.assertTrue(client.post('/spotify', json=dict(mode='weather', upNext=True)).json['upNext'])
        for invalid in (None, 'true', 1, [], {}):
            self.assertEqual(client.post('/spotify', json=dict(enabled=False, upNext=invalid)).status_code, 400)
            self.assertTrue(server.spotify.enabled)
        self.assertFalse(client.post('/spotify', json=dict(upNext=False)).json['upNext'])
