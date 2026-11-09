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

Use the **Ticker speed** slider on that page to change scrolling from 0 to 100
pixels per second; 0 pauses it. Speed defaults to 18 pixels per second and resets
when the app restarts. Movement uses elapsed time so the chosen speed stays
consistent when the emulator's frame rate changes.

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
