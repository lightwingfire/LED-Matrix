# LED Matrix

Clock, weather, and scrolling news for a 128 x 32 RGB matrix. On Windows,
the display runs in a browser using RGBMatrixEmulator.

## Run on Windows

Open PowerShell in the project folder. With the existing `venv`:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe main.py
```

For a fresh checkout, install Python 3.11 and create an environment first:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Open http://localhost:8888 for the matrix and http://127.0.0.1:5000
for the brightness slider. Press Ctrl+C in PowerShell to stop.

The controls page is a responsive React dashboard served by Flask at the same
address. It includes brightness, ticker speed, weather location, and the current
news rotation. The old page's schedule inputs did not control the backend;
automatic brightness scheduling is labeled as unavailable.

### Edit the React interface

Source files live in `frontend/`. With Node.js 22.12+ or 24 installed:

```powershell
npm ci --cache .npm-cache
npm run build
```

Reload http://127.0.0.1:5000 after building. Use `npm run dev` to rebuild on
source changes while the Python app runs in another terminal; reload the browser
to see updates. The bundled files in `static/ui/` are included in the repository,
so normal Windows and Raspberry Pi operation needs neither Node.js nor a CDN.
Include rebuilt assets when deploying interface changes to the Pi.

### Build and deploy to the Raspberry Pi

Install the local deployment dependencies once:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements-deploy.txt
```

Keep `PI_IP`, `PI_UN`, and `PI_PSW` in your ignored local `settings.toml`.
Then build and deploy with:

```powershell
npm run deploy
```

The script builds React, packages the Python app and display assets, connects
over SSH, and finds the existing `~/main/test/test` installation. It backs up
the files it replaces under `.deploy-backups/` on the Pi, restarts the app using
`run.sh`, and verifies the served JavaScript, CSS, and ticker API. Failed health
checks trigger an attempt to restore the previous files and restart the app.
The reboot cron entry, virtual environment, settings, and news cache stay intact.
Credentials are neither printed nor uploaded. SSH host keys are remembered in
the ignored local `.deploy/known_hosts` file after the first connection.

To check the connection without deploying, run `npm run deploy -- -Inspect`.
To build a local package without connecting, run `npm run deploy -- -BuildOnly`.
Use `-RemoteDir /absolute/project/path` or `-WebPort 5001` to override defaults.
The board must already have its Python dependencies and native matrix driver,
and the SSH account needs passwordless sudo as used by `run.sh`.

The underlying Python script also works outside PowerShell:
`python scripts/deploy_board.py` (options: `--inspect`, `--build-only`,
`--remote-dir`, `--web-port`).

Use the **Ticker speed** slider on that page to change scrolling from 0 to 100
pixels per second; 0 pauses it. Speed defaults to 18 pixels per second and resets
when the app restarts. Movement uses elapsed time so the chosen speed stays
consistent when the emulator's frame rate changes.

The **Ticker tape** toggle in **News** hides the ticker and stops its movement.
Turning it back on resumes at the same speed and position. Clock, weather, and
news links remain available. The ticker defaults to on when the app restarts.

Press **FISH** to enter aquarium mode. This displays a blue-to-black water
gradient with diagonal light bands that drift right at different speeds,
wrap around, and fade in and out independently,
and pauses the clock, weather, and ticker display. The brightness
slider also controls the aquarium. Press **FISH** again to restore the other
elements with their existing settings.
The app starts with FISH mode off.

The fish chooses random destinations above the sand, turns toward them in 3D,
and swims at varying speeds. Its parts keep their fixed drawing order and
delayed head-to-tail motion. Turns ease in and out, with each body section
following more slowly toward the tailfin while remaining connected.
`Fish.buildFish()` generates varied sizes for its seven overlapping parts when
the fish is initialized. `buildFish(seed=7)` can reproduce a particular shape.

While FISH mode is on, **Generate new sand** creates a new sand profile using
the current sand settings. It stays fixed between frames and keeps neighboring
columns within one pixel of each other.
The **add fish** button adds another independently swimming fish and a row in
the fish table. Each row shows its current cruise speed in pixels per second,
its generation seed, and a **gen new fish** button that rebuilds only that fish.
Each row also has **delete fish**, which removes that fish from the aquarium.
You can delete every fish and add new ones afterward.
The table updates every second. Fish keep stable row IDs when regenerated;
water, sand, brightness, and shadow mode are preserved. The app starts with
one fish, and added fish reset when the app restarts.
**Shadow mode** makes every fish part dark blue. Turn it off to restore the
fish's colors. New fish get random part colors; generating one while shadow
mode is on keeps the shadow appearance. Shadow mode resets to off on restart.

Sand generation uses `roughnessX` for the number of columns between height-change
attempts and `roughnessY` for the percentage chance of a one-pixel height change
at each attempt. Defaults are `roughnessX=4` and `roughnessY=50`.
Setting `roughnessY=0` makes the sand flat; `100` changes height at every attempt.

The settings page also includes a weather ZIP code field. Enter a US ZIP code
or ZIP+4 and click **Save ZIP code**. It saves `WEATHER_LOCATION` in your local
`settings.toml` and refreshes the forecast automatically. If a refresh is already
running, the new ZIP code is fetched when that request finishes.

The page also lists the news stories loaded by the LED ticker, with article
links, sources, and publication dates. It checks for updated stories every
30 seconds without making additional requests to the news provider. Cached
stories and refresh failures are labeled so you can tell when the feed is stale.
The ticker plays each valid, distinct headline once per shuffled rotation before
repeating. Refreshing the feed leaves already queued stories intact.

## Local settings

### Spotify now playing

By default, Spotify adds the green message `🎵 Now Play: {song} - {artist}`
between news headlines in the ticker. It follows the ticker's speed, brightness,
and on/off controls. A small pixel music note represents the emoji on the board.
Changed songs replace queued music entries; pausing or disconnecting removes them.
The dashboard's **Spotify display** selector offers three modes:

- **Ticker tape** (default): keeps the clock and weather, adding green music entries.
- **Replace weather when playing**: shows 20×20 album art with a 2-pixel margin and scrolling song details
  in an expanded weather area (x=58–127, y=0–23). The cover is shifted 10 pixels
  left to give the title and artist 10 more pixels of horizontal space.
  The current song is never repeated in the ticker in this mode.
  Enable **Up Next in ticker tape** to insert a green `🎵 Up Next: {song} - {artist}`
  message between news headlines instead. Up Next defaults to off and resets on restart.
  Enable it before connecting, or click **Reconnect Spotify** after enabling it to
  grant the additional `user-read-playback-state` permission for the
  [queue endpoint](https://developer.spotify.com/documentation/web-api/reference/get-queue).
  Empty queues, podcasts, paused playback, stale data, and queue failures remove the entry.
- **Spotify focus**: fills the screen with 24×24 album art with a 4-pixel margin, song, artist, and progress.
  Above the progress bar, the album release year is aligned left and total song duration
  (`m:ss`) is aligned to the far right, using the ticker's 5×8 font.

Weather and focus modes require the actual album cover. While artwork is loading
or unavailable, the normal display remains visible. Focus falls back to a now-playing
ticker entry; weather mode keeps now-playing entries out of the ticker even without art.
Paused, stale, or disconnected playback restores the normal display.
FISH mode takes priority. The dashboard also has connection and **Hide on board**
controls. Playback is read-only: music still plays on your Spotify device.
Mode resets to ticker on restart.

`sample_album_art(image, size)` in `spotify.py` accepts a Pillow image and either
a square size (such as `24` or `32`) or `(width, height)`. It returns an RGB image
using LANCZOS sampling and black letterboxing to preserve the complete cover.
Pass `preserve_aspect=False` to fill a rectangular size exactly, as the weather layout does.
Downloads run in the background; sampled sizes are cached for each album.
Spotify is polled in a background thread every five seconds; network requests never
run on the display loop. After 30 seconds without fresh data, the normal display returns.
Podcasts, ads, and unavailable tracks also use the normal display.

1. Create an app in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
   Select Web API and register this exact redirect URI:
   `http://127.0.0.1:5000/spotify/callback`.
2. Add the following root-level settings to the settings file used by the board
   (`settings.toml`, or `runtime/settings.toml` when launched with that file):

   ```toml
   SPOTIFY_CLIENT_ID = "your-app-client-id"
   SPOTIFY_REDIRECT_URI = "http://127.0.0.1:5000/spotify/callback"
   ```

   No client secret is needed. This integration uses
   [Authorization Code with PKCE](https://developer.spotify.com/documentation/web-api/tutorials/code-pkce-flow)
   with `user-read-currently-playing` permission and optional `user-read-playback-state`
   permission for Up Next. Environment variables override settings.
3. Restart the app and open `http://127.0.0.1:5000`. Click **Connect Spotify**,
   sign in, then start playing music.

To sign in directly from the Pi's LAN dashboard without an SSH tunnel:

1. Open the board's dashboard in your browser and click **Connect Spotify**.
   Sign-in opens in a new tab; keep the original dashboard tab open.
2. Complete Spotify sign-in. The new tab will redirect to
   `http://127.0.0.1:5000/spotify/callback?...`. It may fail to load or show a
   sign-in error because that address points to your browser's computer.
3. Copy the **entire URL from the address bar**. Return to the original dashboard,
   expand **Finish sign-in by pasting the callback URL**, paste it, and click
   **Finish connection**.

Complete this within 10 minutes using the same browser and dashboard address where
you clicked Connect. The board must stay running during sign-in. Start a fresh
connection after a restart, expired attempt, or previously used callback.
The board validates the callback address, browser cookie, state, and PKCE verifier;
it never visits the pasted URL. Tokens remain on the board.

Alternatively, establish a tunnel from your computer before opening the dashboard:

```powershell
ssh -N -L 5000:127.0.0.1:5000 your-pi-user@your-pi-address
```

Leave that terminal running, then open `http://127.0.0.1:5000` on the same computer
and connect Spotify there. Stop any local copy of this app using port 5000 first.
The callback reaches the Pi through the tunnel. For a different local port, change
the tunnel, browser address, redirect setting, and Spotify app registration together.
Spotify requires [HTTPS or an explicit loopback IP for redirects](https://developer.spotify.com/documentation/web-api/concepts/redirect_uri);
a plain HTTP Pi LAN address and `localhost` are not accepted.

Tokens are saved beside the active settings file in `.spotify-tokens.json`, ignored
by Git and excluded from deployment packages. The connection survives restarts;
**Disconnect** removes the local tokens. To revoke the app's permission entirely,
remove it from your Spotify account's connected apps. Display visibility resets
to on when the app restarts. Each installation needs its own connection.
If Spotify returns access denied, check your app's user allowlist and the current
[development-mode requirements](https://developer.spotify.com/documentation/web-api/concepts/quota-modes).

### News and weather settings

The app automatically reads `settings.toml` beside `main.py`. This file is
ignored by Git. Keep your existing file, or create one with your own values:

```toml
NEWS_API_KEY = "your-newsapi-key"
WEATHERAPI_KEY = "your-weatherapi-key"
WEATHER_LOCATION = "08865"
```

Environment variables override values in the file. Network refresh failures
leave the display running with existing news and weather values. Windows uses
the computer's local clock and network connection; the CircuitPython Wi-Fi and
time-zone settings are not used by this port.

The brightness server defaults to `127.0.0.1`. Optional `WEB_HOST`, `WEB_PORT`,
and `EMULATOR_PORT` settings can change the server address and ports. If another
copy is already running, stop it first or choose different ports, for example:

```powershell
$env:WEB_PORT = "5001"
$env:EMULATOR_PORT = "8889"
.\venv\Scripts\python.exe main.py
```

In that example, use http://127.0.0.1:5001 and http://localhost:8889.

## Existing Raspberry Pi installation

`run.sh` uses the Pi's existing `venv/bin/python` and native matrix driver.
It supports reboot cron entries that invoke `sh run.sh` and exposes the web
controls on port 5000 on the local network. The Windows emulator dependencies
are not needed for this deployment.

On the deployed Pi, application settings live in `runtime/settings.toml`.
This private directory is writable by the account used after the matrix driver
drops privileges, so saving a ZIP code works without making the source writable.
`LED_SETTINGS_FILE` can select another settings file. SSH credentials are not
copied to the Pi. Driver refresh-rate logging is off by default; set
`SHOW_REFRESH_RATE=1` when running Python directly to enable it for diagnostics.

The native driver uses software pulse timing by default to avoid hardware PWM
waits that can freeze display updates and web controls. Set `HARDWARE_PULSING=1`
to opt into hardware timing. `/health` returns success only while display frames
are advancing; deployment verifies this as well as the website assets.
