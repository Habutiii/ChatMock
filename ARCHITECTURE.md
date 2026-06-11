# ChatMock Architecture

## Overview

ChatMock is a local or self-hosted HTTP service that exposes OpenAI-compatible and Ollama-compatible endpoints, then proxies supported requests to ChatGPT upstream using the ChatGPT credentials stored by `chatmock login`.

It is not a local model runner and it is not backed by the Codex CLI process. The core job is protocol translation and session handling around an authenticated upstream ChatGPT account.

## Request Flow

1. A client sends a request to ChatMock over HTTP or WebSocket.
2. ChatMock applies inbound security checks.
3. ChatMock normalizes the request into the upstream Responses format.
4. ChatMock loads the stored ChatGPT access token and account id.
5. ChatMock forwards the request to the ChatGPT upstream endpoint.
6. ChatMock streams or transforms the upstream response back into the client-facing API shape.

## Main Components

- `chatmock/cli.py`
  Starts login and serve flows.

- `chatmock/app.py`
  Builds the Flask app, registers routes, and applies inbound auth checks.

- `chatmock/routes_openai.py`
  Implements OpenAI-compatible HTTP routes such as `/v1/models`, `/v1/chat/completions`, and `/v1/responses`.

- `chatmock/routes_ollama.py`
  Implements Ollama-compatible routes such as `/api/tags` and `/api/chat`.

- `chatmock/websocket_routes.py`
  Implements the `/v1/responses` WebSocket interface.

- `chatmock/security.py`
  Applies inbound bearer-token authentication and persistent IP blacklisting after repeated failed attempts.

- `chatmock/upstream.py`
  Builds upstream headers and sends requests to ChatGPT.

- `chatmock/oauth.py`
  Handles the ChatGPT login flow and token acquisition.

- `chatmock/session.py`
  Tracks request/session reuse state for the Responses API.

## Trust Boundaries

There are two separate trust boundaries in this system:

- Client to ChatMock
  This is your public or semi-public API edge. This is where bearer-token auth, network controls, TLS termination, and abuse protection matter.

- ChatMock to ChatGPT upstream
  This is the proxy-to-upstream hop using the stored ChatGPT credentials. Compromise here means compromise of the upstream ChatGPT account.

## Authentication Model

### Upstream Authentication

ChatMock authenticates to ChatGPT using credentials obtained from `chatmock login` and stored under `CHATGPT_LOCAL_HOME` or the default local home directory.

### Inbound Client Authentication

ChatMock can require `Authorization: Bearer <token>` for all non-health inbound routes.

Supported token sources:

- `CHATMOCK_API_KEY_FILE`
  Preferred option. File path containing one token per line. This file is re-read on each request. If unset, ChatMock defaults to `CHATGPT_LOCAL_HOME/security/api_tokens.txt`.

- `CHATMOCK_API_KEYS`
  Comma-separated bearer tokens from environment.

- `CHATMOCK_API_KEY`
  Backward-compatible single bearer token from environment.

Health endpoints remain open by design:

- `/`
- `/health`

This allows Docker and other health checks to work without a token.

## Persistence

ChatMock uses on-disk state for:

- ChatGPT login credentials
- installation id and local state
- persistent IP blacklist
- optional bearer-token file

Recommended Docker-backed persistent paths:

- `/data` for ChatGPT login state
- `/data/security/ip_blacklist.json` for blacklist state
- `/data/security/api_tokens.txt` for inbound bearer tokens

## Public API Surface

Current public-facing interfaces:

- OpenAI-compatible HTTP routes under `/v1`
- OpenAI-compatible WebSocket route at `/v1/responses`
- Ollama-compatible HTTP routes under `/api`
- health routes at `/` and `/health`

## Current Security Controls

Current controls implemented in this repository:

- inbound bearer-token authentication for non-health routes
- constant-time token comparison
- optional token list loaded from disk
- persistent IP blacklist after repeated failed auth attempts
- CORS response headers

## Public Exposure Guidance

The current bearer-token check is helpful, but it is not sufficient by itself for a directly exposed internet-facing API.

Minimum recommended deployment shape:

1. Put ChatMock behind a reverse proxy such as Nginx, Caddy, Traefik, or a cloud load balancer.
2. Terminate TLS at the proxy and redirect all HTTP to HTTPS.
3. Run ChatMock behind the proxy on a private network, not directly on the public interface.
4. Replace Flask development serving with a production WSGI / ASGI serving setup appropriate for Flask and WebSocket traffic.
5. Restrict who can reach the service with network policy where possible.

## Recommended Additional Security Features

If this service will be public-facing, these are the next controls to add around or in front of it.

### High Priority

- Reverse proxy with TLS only
  Do not expose plain HTTP on the public internet.

- Production app serving
  Do not rely on Flask's development server for edge deployment.

- Network allowlisting where possible
  If only known tools or office IPs need access, restrict by source IP at the proxy or firewall.

- Reverse-proxy rate limiting
  Apply request-rate and connection-rate limits at Nginx, Traefik, Cloudflare, or your load balancer instead of only inside the Flask app.

- Secret rotation
  Use `CHATMOCK_API_KEY_FILE` so bearer tokens can be rotated or revoked without restarting the service.

- Request and auth audit logs
  Log remote IP, route, auth success or failure, and upstream status without logging bearer tokens.

### Medium Priority

- Separate admin and public surfaces
  Keep login flows, debug flows, or future admin endpoints off the public listener.

- Web Application Firewall or managed edge protection
  Useful if the service is broadly internet reachable.

- mTLS or a second upstream identity layer
  Appropriate for service-to-service traffic where you control the client.

- Request size limits and timeout policy
  Prevent oversized uploads and long-running abusive connections.

- Per-token quota or rate caps
  Useful when multiple consumers share the same deployment.

### Optional Depending on Threat Model

- Geo restrictions
- VPN-only access
- Signed client requests
- Cloud identity-aware proxy in front of ChatMock

## Security Gaps To Be Aware Of

These are current limitations of the repository as it stands today:

- The built-in server path still uses Flask development serving through `app.run`.
- Health routes are intentionally unauthenticated.
- There is no built-in reverse-proxy rate limiting.
- There is no built-in per-token quota, expiry, or rotation metadata.
- There is no built-in structured audit log for auth events.
- CORS is permissive and should be reviewed if the service is browser-accessible from untrusted origins.

## Practical Deployment Recommendation

For a public deployment, prefer this shape:

1. Internet
2. Reverse proxy or cloud edge with TLS, IP filtering, and rate limiting
3. Private ChatMock container or process
4. Outbound ChatGPT upstream API access

For a low-risk private deployment, use:

1. VPN or private network
2. ChatMock on `127.0.0.1:9099` or another loopback-only bind
3. ChatMock with bearer token file
4. Docker volume mounted at `/data`

## Suggested Next Steps

If you want this to be genuinely public-facing, the next code or infrastructure work should be:

1. Add structured auth and access logs.
2. Add explicit trusted-proxy handling and document `X-Forwarded-For` expectations.
3. Put a reverse-proxy example in the repo with TLS and rate limits.
4. Add request body size limits and connection timeouts.
5. Add token metadata support such as named tokens, created-at, expires-at, and revoke reason.
