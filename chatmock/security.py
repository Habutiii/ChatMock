from __future__ import annotations

import hmac
import json
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import time


@dataclass(frozen=True)
class AuthDecision:
    allowed: bool
    status_code: int = 200
    message: str = ""


class ApiSecurityManager:
    def __init__(
        self,
        api_keys: tuple[str, ...] | list[str] | None,
        *,
        api_key_file: Path | None,
        blacklist_attempts: int,
        window_seconds: int,
        blacklist_path: Path,
    ) -> None:
        self.api_keys = tuple(token for token in (api_keys or ()) if isinstance(token, str) and token)
        self.api_key_file = Path(api_key_file) if api_key_file is not None else None
        self.blacklist_attempts = max(1, int(blacklist_attempts))
        self.window_seconds = max(1, int(window_seconds))
        self.blacklist_path = Path(blacklist_path)
        self._lock = threading.Lock()
        self._failed_attempts: dict[str, list[float]] = {}
        self._blacklisted_ips = self._load_blacklist()

    @property
    def enabled(self) -> bool:
        if self.api_keys:
            return True
        return self.api_key_file is not None

    def authorize(self, provided_token: str | None, client_ip: str | None) -> AuthDecision:
        if not self.enabled:
            return AuthDecision(True)

        ip = (client_ip or "unknown").strip() or "unknown"
        valid_tokens = self._get_valid_tokens()

        if not valid_tokens:
            return AuthDecision(
                False,
                status_code=503,
                message="Authentication token file is missing or empty.",
            )

        with self._lock:
            if ip in self._blacklisted_ips:
                return AuthDecision(False, status_code=403, message="IP address is blacklisted.")

            if provided_token and self._matches_token(provided_token, valid_tokens):
                self._failed_attempts.pop(ip, None)
                return AuthDecision(True)

            failures = self._prune_failures(ip)
            failures.append(time())
            count = len(failures)
            self._failed_attempts[ip] = failures

            if count >= self.blacklist_attempts:
                self._blacklisted_ips[ip] = {
                    "blocked_at": datetime.now(UTC).isoformat(),
                    "failures": count,
                }
                self._persist_blacklist()
                return AuthDecision(False, status_code=403, message="IP address has been blacklisted after repeated failed authentication attempts.")

            return AuthDecision(False, status_code=401, message="Missing or invalid Authorization bearer token.")

    def _get_valid_tokens(self) -> tuple[str, ...]:
        tokens = list(self.api_keys)
        tokens.extend(self._load_api_keys_from_file())
        return tuple(dict.fromkeys(tokens))

    def _load_api_keys_from_file(self) -> list[str]:
        if self.api_key_file is None:
            return []
        try:
            lines = self.api_key_file.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            return []
        except Exception:
            return []

        tokens: list[str] = []
        for raw_line in lines:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            tokens.append(line)
        return tokens

    def _matches_token(self, provided_token: str, valid_tokens: tuple[str, ...]) -> bool:
        for token in valid_tokens:
            if hmac.compare_digest(provided_token, token):
                return True
        return False

    def _prune_failures(self, ip: str) -> list[float]:
        cutoff = time() - self.window_seconds
        kept = [stamp for stamp in self._failed_attempts.get(ip, []) if stamp >= cutoff]
        if kept:
            self._failed_attempts[ip] = kept
        else:
            self._failed_attempts.pop(ip, None)
        return kept

    def _load_blacklist(self) -> dict[str, dict[str, object]]:
        try:
            data = json.loads(self.blacklist_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except Exception:
            return {}

        ips = data.get("ips")
        if not isinstance(ips, dict):
            return {}
        return {str(ip): value for ip, value in ips.items() if isinstance(value, dict)}

    def _persist_blacklist(self) -> None:
        self.blacklist_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "updated_at": datetime.now(UTC).isoformat(),
            "ips": self._blacklisted_ips,
        }
        self.blacklist_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def get_request_ip(headers: dict[str, str] | object, remote_addr: str | None) -> str:
    return (remote_addr or "unknown").strip() or "unknown"


def get_bearer_token(headers: dict[str, str] | object) -> str | None:
    if not hasattr(headers, "get"):
        return None
    authorization = headers.get("Authorization")
    if not isinstance(authorization, str):
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return None
    value = token.strip()
    return value or None
