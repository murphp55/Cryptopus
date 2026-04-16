"""Tests for the credentials module."""
import json
import os
import tempfile
from unittest.mock import patch, MagicMock

from cryptopus.credentials import (
    migrate_from_config_json,
    save_exchange_keys,
    load_exchange_keys,
    is_keyring_available,
)


class TestMigrateFromConfigJson:
    def test_returns_empty_when_no_config_and_no_keyring(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "config.json")
            with patch("cryptopus.credentials.is_keyring_available", return_value=False):
                with patch("cryptopus.credentials.load_exchange_keys", return_value=None):
                    result = migrate_from_config_json(config_path=path)
            assert result == {}

    def test_reads_config_json_when_keyring_unavailable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "config.json")
            config = {"exchanges": {"coinbase": {"apiKey": "real_key", "secret": "real_secret"}}}
            with open(path, "w") as f:
                json.dump(config, f)
            with patch("cryptopus.credentials.is_keyring_available", return_value=False):
                with patch("cryptopus.credentials.load_exchange_keys", return_value=None):
                    result = migrate_from_config_json(config_path=path)
            assert "coinbase" in result
            assert result["coinbase"]["apiKey"] == "real_key"

    def test_skips_placeholder_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "config.json")
            config = {"exchanges": {"coinbase": {"apiKey": "YOUR_KEY", "secret": "YOUR_SECRET"}}}
            with open(path, "w") as f:
                json.dump(config, f)
            with patch("cryptopus.credentials.is_keyring_available", return_value=False):
                with patch("cryptopus.credentials.load_exchange_keys", return_value=None):
                    result = migrate_from_config_json(config_path=path)
            assert result == {}

    def test_uses_keyring_when_available(self):
        stored = {"binance": {"apiKey": "from_keyring", "secret": "secret"}}
        with patch("cryptopus.credentials.load_exchange_keys", return_value=stored):
            result = migrate_from_config_json()
        assert result == stored

    def test_migrates_to_keyring_and_renames_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "config.json")
            config = {"exchanges": {"kraken": {"apiKey": "real_key", "secret": "real_secret"}}}
            with open(path, "w") as f:
                json.dump(config, f)

            with patch("cryptopus.credentials.load_exchange_keys", return_value=None):
                with patch("cryptopus.credentials.is_keyring_available", return_value=True):
                    with patch("cryptopus.credentials.save_exchange_keys", return_value=True):
                        result = migrate_from_config_json(config_path=path)

            assert "kraken" in result
            # config.json should be renamed to .bak
            assert not os.path.exists(path)
            assert os.path.exists(path + ".bak")


class TestKeyringFunctions:
    def test_save_and_load_roundtrip(self):
        keys = {"coinbase": {"apiKey": "abc", "secret": "xyz"}}
        mock_store = {}

        def mock_set(service, user, data):
            mock_store[(service, user)] = data

        def mock_get(service, user):
            return mock_store.get((service, user))

        with patch("cryptopus.credentials.is_keyring_available", return_value=True):
            with patch("cryptopus.credentials.keyring") as mock_kr:
                mock_kr.set_password = mock_set
                mock_kr.get_password = mock_get
                assert save_exchange_keys(keys) is True
                loaded = load_exchange_keys()
                assert loaded == keys
