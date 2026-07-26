from __future__ import annotations

import os
from pathlib import Path


def load_env_file(path: str | Path = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists() or not env_path.is_file():
        return

    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip()
        if value and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        os.environ[key] = value


load_env_file()


CLIENT_ID_DEFAULT = os.getenv("CHATGPT_LOCAL_CLIENT_ID") or "app_EMoamEEZ73f0CkXaXp7hrann"
OAUTH_ISSUER_DEFAULT = os.getenv("CHATGPT_LOCAL_ISSUER") or "https://auth.openai.com"
OAUTH_TOKEN_URL = f"{OAUTH_ISSUER_DEFAULT}/oauth/token"
ORIGINATOR = "chatmock"

CHATGPT_RESPONSES_URL = "https://chatgpt.com/backend-api/codex/responses"


def _get_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def get_data_root() -> Path:
    configured = (os.getenv("CHATGPT_LOCAL_HOME") or "").strip()
    if configured:
        return Path(configured)
    return Path.cwd() / "data"


def get_server_api_key_file() -> Path | None:
    value = (os.getenv("CHATMOCK_API_KEY_FILE") or "").strip()
    if value:
        return Path(value)
    return get_data_root() / "security" / "api_tokens.txt"


def get_auth_blacklist_attempts() -> int:
    return max(1, _get_int_env("CHATMOCK_AUTH_BLACKLIST_ATTEMPTS", 10))


def get_auth_window_seconds() -> int:
    return max(1, _get_int_env("CHATMOCK_AUTH_WINDOW_SECONDS", 300))


def get_auth_blacklist_path() -> Path:
    configured = (os.getenv("CHATMOCK_AUTH_BLACKLIST_PATH") or "").strip()
    if configured:
        return Path(configured)
    return get_data_root() / "security" / "ip_blacklist.json"
