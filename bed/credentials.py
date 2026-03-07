import json
import os
from pathlib import Path

CREDENTIALS_DIR = Path.home() / ".bed"
CREDENTIALS_FILE = CREDENTIALS_DIR / "credentials.json"


def load_credentials() -> dict:
    if not CREDENTIALS_FILE.exists():
        return {}
    return json.loads(CREDENTIALS_FILE.read_text())


def save_credentials(creds: dict) -> None:
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_FILE.write_text(json.dumps(creds, indent=2))
    os.chmod(CREDENTIALS_FILE, 0o600)


def set_credential(key: str, value: str) -> None:
    creds = load_credentials()
    creds[key] = value
    save_credentials(creds)


def get_credential(key: str, default: str | None = None) -> str | None:
    return load_credentials().get(key, default)


def get_aws_credentials() -> tuple[str, str] | None:
    creds = load_credentials()
    access_key = creds.get("aws_access_key_id")
    secret_key = creds.get("aws_secret_access_key")
    if access_key and secret_key:
        return access_key, secret_key
    return None


def get_gcp_credentials_path() -> str | None:
    return get_credential("gcp_service_account_key_path")
