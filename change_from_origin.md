# Changes From Upstream

This repository is a fork of `RayBytes/ChatMock`:

- Fork repo: `https://github.com/Habutiii/ChatMock`
- Upstream repo: `https://github.com/RayBytes/ChatMock`
- Compared branch: `main`
- Fork-point / merge-base: `1f7a632` (`fix git workflow bug & badge`)

Status at the time of this summary:

- Fork is `4` commits ahead of upstream `main`
- Fork is `4` commits behind upstream `main`
- This summary is based on `git diff upstream/main...HEAD`

## Fork-Only Functional Changes To Preserve

These are the behavior changes that exist in this fork and should be retained when updating from upstream later.

### 1. Inbound bearer-token auth for all non-health routes

Main behavior:

- All non-health HTTP routes require `Authorization: Bearer <token>` when auth is enabled.
- Health routes stay open:
  - `/`
  - `/health`
- The same auth check is applied to the WebSocket `/v1/responses` handshake.

Implementation details:

- Flask `before_request` guard in `chatmock/app.py`
- WebSocket auth check in `chatmock/websocket_routes.py`
- Token parsing and auth logic in `chatmock/security.py`

Important retention notes:

- This is not just documentation. It is active request gating.
- If auth is configured incorrectly, the fork intentionally fails closed on protected routes.

### 2. Token file support with hot reload

Main behavior:

- Valid inbound tokens are read from a file, one token per line.
- The token file is read on every request, so token rotation does not require a restart.
- Comment lines beginning with `#` are ignored.

Current default path:

- `CHATMOCK_API_KEY_FILE`, if set
- otherwise `CHATGPT_LOCAL_HOME/security/api_tokens.txt`
- with the current Docker defaults, that resolves to `/app/data/security/api_tokens.txt`

Implementation details:

- Path helpers in `chatmock/config.py`
- File-backed token loading in `chatmock/security.py`

Important retention notes:

- Hot reload is part of the current behavior.
- Missing or empty token file returns `503` on protected routes instead of silently disabling auth.

### 3. Persistent IP blacklist after repeated failed auth

Main behavior:

- Failed bearer-token attempts are tracked per client IP.
- After a configured number of failures inside a rolling window, the IP is blacklisted.
- Blacklist state is persisted on disk and survives process restart.

Current settings:

- `CHATMOCK_AUTH_BLACKLIST_ATTEMPTS` default `10`
- `CHATMOCK_AUTH_WINDOW_SECONDS` default `300`
- `CHATMOCK_AUTH_BLACKLIST_PATH` default `CHATGPT_LOCAL_HOME/security/ip_blacklist.json`

Implementation details:

- Implemented in `chatmock/security.py`
- Wired into app startup in `chatmock/app.py`

Important retention notes:

- The blacklist is intentionally based on `REMOTE_ADDR`.
- `X-Forwarded-For` is intentionally ignored in current logic.
- Once blacklisted, even a valid token is rejected from that IP.

### 4. Local `.env` loading at import time

Main behavior:

- `chatmock/config.py` now loads a local `.env` file automatically if present.
- Existing environment variables still win over values from the file.

Important retention notes:

- This changes startup/config behavior outside Docker too.
- If upstream changes config loading later, preserve this precedence model if you want the fork behavior unchanged.

### 5. Default serving and deployment now assume local self-hosted usage

Main behavior:

- Default server port changed from `8000` to `9099`
- GUI defaults also changed to `9099`
- Docker runtime home changed from `/data` to `/app/data`
- Docker Compose now builds the local image instead of pulling a published image
- Docker Compose persists runtime state in repo-local `./data`
- Published service port is bound to loopback: `127.0.0.1:9099:9099`

Files involved:

- `chatmock/cli.py`
- `gui.py`
- `docker/entrypoint.sh`
- `Dockerfile`
- `docker-compose.yml`
- `.env.example`
- `README.md`
- `DOCKER.md`

Important retention notes:

- These are operational changes, not just docs.
- Any later upstream update that restores port `8000`, `/data`, or registry-image compose flow would change current deployment behavior.

## Tests Added For Fork Behavior

The fork adds coverage for the new behavior and these tests are useful as a retention checklist during future updates.

- `tests/test_routes.py`
  Covers:
  - health remaining open
  - bearer-token requirement
  - fail-closed empty token file
  - multiple valid tokens
  - token-file hot reload
  - persistent IP blacklist
  - use of `REMOTE_ADDR` instead of `X-Forwarded-For`

- `tests/docker_smoke_test.py`
  Adds a deployment smoke test for:
  - `/health`
  - protected `/v1/models`
  - bearer-token success/failure cases
  - optional end-to-end chat request

## Documentation Added In Fork

These files are new in the fork and describe the intended current behavior:

- `ARCHITECTURE.md`
  Architecture and deployment/security notes

- `support_request_schema.md`
  Practical request-schema support matrix

These are useful reference documents during a future rebase, but they are secondary to the actual code and tests.

## File-Level Map Of Fork Changes

- `chatmock/app.py`
  Adds global auth enforcement and initializes the security manager.

- `chatmock/security.py`
  New module for token auth, failed-attempt tracking, and persistent blacklist storage.

- `chatmock/websocket_routes.py`
  Applies the same inbound auth model to WebSocket requests.

- `chatmock/config.py`
  Adds `.env` loading and security-path/config helpers.

- `chatmock/cli.py`
  Changes default serve port to `9099`.

- `gui.py`
  Changes GUI/server defaults to `9099`.

- `Dockerfile`
  Prepares `/app/data/security` and exposes `9099`.

- `docker-compose.yml`
  Switches to local build, loopback-only published port, and bind-mounted `./data`.

- `docker/entrypoint.sh`
  Changes default runtime home and server port.

- `.env.example`, `README.md`, `DOCKER.md`
  Updated to match the new auth and deployment behavior.

- `tests/test_routes.py`, `tests/docker_smoke_test.py`
  Add regression coverage for fork-specific behavior.

## Upstream Changes Not Yet In This Fork

At the time of comparison, upstream `main` has these commits that are not in this fork:

- `122fab6` `Fix port mapping (#99)`
- `4b9817f` `fix(stream): emit a single finish_reason for tool-call chat completions (#114)`
- `f497207` `add gpt-5.6 series`
- `7a14223` `remove codex instrunctions, not needed anymore`

When updating from upstream later, expect conflicts or behavior decisions around:

- port and deployment assumptions
- stream output behavior
- model registry changes
- prompt / instruction handling

## Practical Merge Checklist

When rebasing or merging upstream later, verify these fork behaviors still work:

1. `/health` is open without a bearer token.
2. `/v1/models` returns `401` without a token when auth is enabled.
3. A valid token from the token file succeeds.
4. Replacing the token file contents changes valid tokens without restart.
5. Empty or missing token file fails closed on protected routes.
6. Repeated failed auth blacklists the client IP and persists to disk.
7. WebSocket `/v1/responses` also enforces bearer auth.
8. Default local port remains `9099` if that is still desired.
9. Docker still uses `/app/data` and persists state via `./data`.

## Suggested Update Strategy Later

If the goal is to update from upstream while keeping fork behavior:

1. Merge or rebase upstream first.
2. Re-run or restore the fork-specific tests in `tests/test_routes.py` and `tests/docker_smoke_test.py`.
3. Resolve conflicts in this order:
   - `chatmock/security.py`
   - `chatmock/app.py`
   - `chatmock/websocket_routes.py`
   - `chatmock/config.py`
   - Docker and port defaults
4. Re-check the docs only after code and tests are correct.

The code-level source of truth for this fork is the auth/security path plus the deployment defaults. Those are the main changes that need to survive an upstream refresh.
