"""Tests for JSON credentials loader (config/credentials.json fallback)."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from src import credentials_loader

_ROOT = Path(__file__).resolve().parent.parent


def test_load_credentials_from_json_missing_file_returns_empty() -> None:
    """When path does not exist, returns empty dict."""
    with patch.dict("os.environ", {}, clear=False):
        with patch.object(
            credentials_loader, "_DEFAULT_PATH", _ROOT / "nonexistent_creds.json"
        ):
            # Force re-read by clearing any module-level cache if present
            result = credentials_loader.load_credentials_from_json()
    assert result == {}


def test_load_credentials_from_json_valid_file_returns_keys() -> None:
    """When file exists and is valid JSON with expected keys, returns api_key and urls."""
    path = _ROOT / "config" / "credentials.json.example"
    if not path.exists():
        pytest.skip("config/credentials.json.example not found")
    with patch.dict("os.environ", {"SKYFI_CREDENTIALS_PATH": str(path)}, clear=False):
        result = credentials_loader.load_credentials_from_json()
    assert "api_key" in result
    assert "api_base_url" in result
    assert "webhook_base_url" in result
    assert "notification_url" in result
    assert result["api_key"] == "your-skyfi-api-key-here"
    assert "platform-api" in result["api_base_url"]


def test_load_credentials_from_json_custom_path_from_env() -> None:
    """SKYFI_CREDENTIALS_PATH is used when set."""
    tmp = _ROOT / "tests" / "fixtures" / "test_creds.json"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(
        json.dumps({"api_key": "test-key", "api_base_url": "https://api.test.com"})
    )
    try:
        with patch.dict(
            "os.environ", {"SKYFI_CREDENTIALS_PATH": str(tmp)}, clear=False
        ):
            result = credentials_loader.load_credentials_from_json()
        assert result.get("api_key") == "test-key"
        assert result.get("api_base_url") == "https://api.test.com"
    finally:
        if tmp.exists():
            tmp.unlink()


def test_load_credentials_from_json_invalid_json_returns_empty() -> None:
    """Invalid JSON returns empty dict (no exception)."""
    tmp = _ROOT / "tests" / "fixtures" / "invalid_creds.json"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text("not valid json {")
    try:
        with patch.dict(
            "os.environ", {"SKYFI_CREDENTIALS_PATH": str(tmp)}, clear=False
        ):
            result = credentials_loader.load_credentials_from_json()
        assert result == {}
    finally:
        if tmp.exists():
            tmp.unlink()
