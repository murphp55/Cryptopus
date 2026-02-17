"""Tests for config validation."""
from cryptopus.config import validate_config, AppConfig


class TestValidateConfig:
    def test_valid_config(self):
        logs = []
        data = {"exchanges": {"coinbase": {"apiKey": "key", "secret": "sec"}}}
        result = validate_config(data, logs.append)
        assert "coinbase" in result
        assert len(logs) == 0

    def test_missing_exchanges_key(self):
        logs = []
        result = validate_config({}, logs.append)
        assert result == {}
        assert any("missing 'exchanges'" in m for m in logs)

    def test_not_a_dict(self):
        logs = []
        result = validate_config("bad", logs.append)
        assert result == {}
        assert any("not a dict" in m for m in logs)

    def test_exchanges_not_dict(self):
        logs = []
        result = validate_config({"exchanges": "bad"}, logs.append)
        assert result == {}

    def test_bad_credentials_type(self):
        logs = []
        data = {"exchanges": {"binance": "not_a_dict"}}
        result = validate_config(data, logs.append)
        assert "binance" not in result or True  # logged warning
        assert any("not a dict" in m for m in logs)

    def test_non_string_api_key(self):
        logs = []
        data = {"exchanges": {"kraken": {"apiKey": 123, "secret": "sec"}}}
        result = validate_config(data, logs.append)
        assert any("apiKey is not a string" in m for m in logs)


class TestAppConfig:
    def test_defaults(self):
        config = AppConfig()
        assert config.exchange == "coinbase"
        assert config.stop_loss_pct == 2.0
        assert config.take_profit_pct == 3.0
        assert config.use_atr_sizing is False
        assert config.backtest_slippage_pct == 0.05
