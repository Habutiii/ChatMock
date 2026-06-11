from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def _request_json(
    url: str,
    *,
    method: str = "GET",
    token: str | None = None,
    payload: dict | None = None,
    timeout: float = 10.0,
) -> tuple[int, object]:
    headers = {"Accept": "application/json"}
    body = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        return exc.code, json.loads(raw) if raw else {}


def wait_for_health(base_url: str, timeout_seconds: float) -> None:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    health_url = f"{base_url.rstrip('/')}/health"
    while time.time() < deadline:
        try:
            status, body = _request_json(health_url, timeout=3.0)
            if status == 200 and isinstance(body, dict) and body.get("status") == "ok":
                return
        except Exception as exc:  # pragma: no cover - polling diagnostics only
            last_error = exc
        time.sleep(1.0)

    if last_error is not None:
        raise RuntimeError(
            "Health check did not succeed before timeout. "
            f"Last error: {last_error}. "
            "If you are using Docker Compose, ensure you started the local image with "
            "`docker compose up -d --build chatmock` and inspect `docker compose ps` / `docker compose logs chatmock`."
        )
    raise RuntimeError(
        "Health check did not succeed before timeout. "
        "If you are using Docker Compose, inspect `docker compose ps` and `docker compose logs chatmock`."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test a Docker-deployed ChatMock instance.")
    parser.add_argument("--base-url", default="http://127.0.0.1:9099", help="ChatMock base URL")
    parser.add_argument("--token", required=True, help="Bearer token expected by ChatMock")
    parser.add_argument(
        "--health-timeout",
        type=float,
        default=30.0,
        help="Seconds to wait for /health before failing",
    )
    parser.add_argument(
        "--skip-chat",
        action="store_true",
        help="Only test health, auth, and model listing. Skip upstream chat completion.",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")

    try:
        wait_for_health(base_url, args.health_timeout)
        print("PASS: /health returned 200")

        status, body = _request_json(f"{base_url}/v1/models")
        if status != 401:
            raise AssertionError(f"Expected 401 without bearer token, got {status}: {body}")
        print("PASS: /v1/models without bearer token returned 401")

        status, body = _request_json(f"{base_url}/v1/models", token=f"{args.token}-wrong")
        if status != 401:
            raise AssertionError(f"Expected 401 with wrong bearer token, got {status}: {body}")
        print("PASS: /v1/models with wrong bearer token returned 401")

        status, body = _request_json(f"{base_url}/v1/models", token=args.token)
        if status != 200:
            raise AssertionError(f"Expected 200 with bearer token, got {status}: {body}")
        print("PASS: /v1/models with correct bearer token returned 200")

        if not isinstance(body, dict) or "data" not in body:
            raise AssertionError(f"Unexpected /v1/models payload: {body}")
        print("PASS: /v1/models returned expected payload")

        if not args.skip_chat:
            status, body = _request_json(
                f"{base_url}/v1/chat/completions",
                method="POST",
                token=args.token,
                payload={
                    "model": "gpt-5.4-mini",
                    "messages": [{"role": "user", "content": "What is today's date? Reply with the date only."}],
                },
                timeout=60.0,
            )
            if status != 200:
                raise AssertionError(f"Expected 200 from chat completion, got {status}: {body}")
            print("PASS: /v1/chat/completions with bearer token returned 200")

            choices = body.get("choices") if isinstance(body, dict) else None
            if not isinstance(choices, list) or not choices:
                raise AssertionError(f"Unexpected chat completion payload: {body}")
            message = choices[0].get("message") if isinstance(choices[0], dict) else None
            content = message.get("content") if isinstance(message, dict) else None
            if not isinstance(content, str) or not content.strip():
                raise AssertionError(f"Unexpected chat completion content: {body}")
            print("PASS: /v1/chat/completions returned expected payload")
            print(f"MODEL DATE RESPONSE: {content.strip()}")

        print("Docker smoke test passed.")
        return 0
    except Exception as exc:
        print(f"Docker smoke test failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
