import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".bed"
CONFIG_FILE = CONFIG_DIR / "config.json"
DB_PATH = CONFIG_DIR / "bed.db"


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    return json.loads(CONFIG_FILE.read_text())


def save_config(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


def set_config_value(key: str, value: str) -> None:
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)


def get_config_value(key: str, default: str | None = None) -> str | None:
    return load_config().get(key, default)
