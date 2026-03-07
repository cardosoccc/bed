import json
from pathlib import Path
from unittest.mock import patch

import pytest

from bed import credentials


@pytest.fixture
def cred_env(tmp_path):
    cred_dir = tmp_path / ".bed"
    cred_file = cred_dir / "credentials.json"
    with (
        patch.object(credentials, "CREDENTIALS_DIR", cred_dir),
        patch.object(credentials, "CREDENTIALS_FILE", cred_file),
    ):
        yield cred_dir, cred_file


def test_load_empty(cred_env):
    assert credentials.load_credentials() == {}


def test_save_and_load(cred_env):
    cred_dir, cred_file = cred_env
    credentials.save_credentials({"key": "value"})
    assert credentials.load_credentials() == {"key": "value"}


def test_set_credential(cred_env):
    credentials.set_credential("aws_access_key_id", "AKIATEST")
    assert credentials.get_credential("aws_access_key_id") == "AKIATEST"


def test_get_credential_default(cred_env):
    assert credentials.get_credential("missing", "default") == "default"


def test_get_aws_credentials(cred_env):
    credentials.set_credential("aws_access_key_id", "AKIA123")
    credentials.set_credential("aws_secret_access_key", "SECRET")
    result = credentials.get_aws_credentials()
    assert result == ("AKIA123", "SECRET")


def test_get_aws_credentials_missing(cred_env):
    assert credentials.get_aws_credentials() is None


def test_get_gcp_credentials_path(cred_env):
    credentials.set_credential("gcp_service_account_key_path", "/path/to/key.json")
    assert credentials.get_gcp_credentials_path() == "/path/to/key.json"


def test_get_gcp_credentials_path_missing(cred_env):
    assert credentials.get_gcp_credentials_path() is None
