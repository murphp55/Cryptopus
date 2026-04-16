"""Secure credential storage using OS keyring.

Uses the system credential manager (Windows Credential Locker,
macOS Keychain, or Linux Secret Service) to store exchange API keys.
Falls back to config.json if keyring is unavailable.
"""
import json
import os
from typing import Callable, Dict, Optional

SERVICE_NAME = "cryptopus"

try:
    import keyring
    _KEYRING_AVAILABLE = True
except ImportError:
    keyring = None  # type: ignore[assignment]
    _KEYRING_AVAILABLE = False


def is_keyring_available() -> bool:
    """Check if OS keyring backend is usable."""
    if not _KEYRING_AVAILABLE:
        return False
    try:
        # Verify a real backend is available (not the fail backend)
        backend = keyring.get_keyring()
        return "fail" not in type(backend).__name__.lower()
    except Exception:
        return False


def save_exchange_keys(exchanges: Dict[str, Dict[str, str]]) -> bool:
    """Save all exchange credentials to the OS keyring.

    Stores as a single JSON blob under the service name.
    Returns True on success, False if keyring is unavailable.
    """
    if not is_keyring_available():
        return False
    try:
        keyring.set_password(SERVICE_NAME, "exchanges", json.dumps(exchanges))
        return True
    except Exception:
        return False


def load_exchange_keys() -> Optional[Dict[str, Dict[str, str]]]:
    """Load exchange credentials from the OS keyring.

    Returns the exchanges dict, or None if not found or keyring unavailable.
    """
    if not is_keyring_available():
        return None
    try:
        data = keyring.get_password(SERVICE_NAME, "exchanges")
        if data is None:
            return None
        return json.loads(data)
    except Exception:
        return None


def delete_exchange_keys() -> bool:
    """Remove stored credentials from the OS keyring."""
    if not is_keyring_available():
        return False
    try:
        keyring.delete_password(SERVICE_NAME, "exchanges")
        return True
    except Exception:
        return False


def migrate_from_config_json(
    config_path: str = "config.json",
    log_fn: Optional[Callable[[str], None]] = None,
) -> Dict[str, Dict[str, str]]:
    """Migrate credentials from config.json to OS keyring.

    If config.json exists and keyring is available:
      1. Read and validate the keys
      2. Store them in the keyring
      3. Rename config.json to config.json.bak

    Returns the exchanges dict regardless of migration outcome.
    """
    _log = log_fn or (lambda _: None)

    # Try keyring first
    keyring_keys = load_exchange_keys()
    if keyring_keys is not None:
        _log("API keys loaded from OS credential manager.")
        return keyring_keys

    # Fall back to config.json
    if not os.path.exists(config_path):
        _log("No API keys found. Add them in Settings > API Keys.")
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        _log(f"Failed to read config.json: {exc}")
        return {}

    exchanges = data.get("exchanges", {})
    if not isinstance(exchanges, dict):
        _log("CONFIG WARNING: 'exchanges' in config.json is not a dict.")
        return {}

    # Filter out placeholder keys
    real_keys = {}
    for name, creds in exchanges.items():
        if isinstance(creds, dict):
            api_key = creds.get("apiKey", "")
            if api_key and api_key != "YOUR_KEY":
                real_keys[name] = creds

    if not real_keys:
        _log("config.json found but contains no real API keys.")
        return {}

    # Attempt migration to keyring
    if is_keyring_available():
        if save_exchange_keys(real_keys):
            _log(f"Migrated {len(real_keys)} exchange key(s) to OS credential manager.")
            # Rename config.json so keys are no longer on disk
            backup_path = config_path + ".bak"
            try:
                os.rename(config_path, backup_path)
                _log(f"Renamed config.json to config.json.bak (keys removed from disk).")
            except OSError:
                _log("WARNING: Could not rename config.json. Delete it manually for security.")
            return real_keys
        else:
            _log("WARNING: Could not save to OS credential manager. Using config.json (insecure).")
    else:
        _log("WARNING: OS keyring not available. Using config.json (insecure). Install 'keyring' for secure storage.")

    return real_keys
