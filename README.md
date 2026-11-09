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

The settings page also includes a weather ZIP code field. Enter a US ZIP code
or ZIP+4 and click **Save ZIP code**. It saves `WEATHER_LOCATION` in your local
`settings.toml` and refreshes the forecast automatically. If a refresh is already
running, the new ZIP code is fetched when that request finishes.

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
