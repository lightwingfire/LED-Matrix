"""Load desktop/Raspberry Pi settings without exposing local credentials."""

import os
import re
import tempfile
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent


def save_weather_location(location):
    """Update only the location, preserving the other local settings."""
    path = PROJECT_DIR / "settings.toml"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    # Only inspect root-level settings, before any TOML table headers.
    header = re.search(r"(?m)^\s*\[", text)
    boundary = header.start() if header else len(text)
    root, tables = text[:boundary], text[boundary:]
    assignment = f'WEATHER_LOCATION = "{location}"'
    root, count = re.subn(r"(?m)^[ \t]*WEATHER_LOCATION[ \t]*=.*$", assignment, root)
    if not count:
        root = assignment + "\n" + root
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=PROJECT_DIR,
                                         prefix=".weather-settings-", suffix=".tmp",
                                         delete=False) as file:
            temporary_path = Path(file.name)
            file.write(root + tables)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    os.environ["WEATHER_LOCATION"] = location


def load_settings():
    path = PROJECT_DIR / "settings.toml"
    if not path.exists():
        return
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            raise RuntimeError(
                "Install project dependencies first: python -m pip install -r requirements.txt"
            ) from None

    with path.open("rb") as file:
        settings = tomllib.load(file)
    for key, value in settings.items():
        if isinstance(value, (str, int, float, bool)):
            # Explicit environment variables take precedence over the local file.
            os.environ.setdefault(key, str(value))
