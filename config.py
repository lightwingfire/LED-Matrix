"""Load desktop/Raspberry Pi settings without exposing local credentials."""

import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent


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
