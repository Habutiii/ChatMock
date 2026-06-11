# Docker Deployment

## Quick Start
1) Setup env:
   cp .env.example .env

2) Login:
   docker compose run --rm --service-ports chatmock-login login

   - The command prints an auth URL, copy paste it into your browser.
   - If your browser cannot reach the container's localhost callback, copy the full redirect URL from the browser address bar and paste it back into the terminal when prompted.
   - Server should stop automatically once it receives the tokens and they are saved.

3) Start the server:
   docker compose up -d --build chatmock

4) Free to use it in whichever chat app you like!

## Configuration
Set options in `.env` or pass environment variables:
- `PORT`: Container listening port (default 9099)
- `CHATMOCK_API_KEY_FILE`: file containing one valid bearer token per line; re-read on each request so you can update it ad hoc. If unset, ChatMock defaults to `/app/data/security/api_tokens.txt`.
- `CHATMOCK_AUTH_BLACKLIST_ATTEMPTS`: failed auth attempts in the rolling window before the client IP is blacklisted on disk
- `CHATMOCK_AUTH_WINDOW_SECONDS`: rolling window used for failed auth tracking
- `CHATMOCK_AUTH_BLACKLIST_PATH`: blacklist file path inside the container, default `/app/data/security/ip_blacklist.json`
- `VERBOSE`: `true|false` to enable request/stream logs
- `CHATGPT_LOCAL_REASONING_EFFORT`: minimal|low|medium|high|xhigh
- `CHATGPT_LOCAL_REASONING_SUMMARY`: auto|concise|detailed|none
- `CHATGPT_LOCAL_REASONING_COMPAT`: legacy|o3|think-tags|current
- `CHATGPT_LOCAL_FAST_MODE`: `true|false` to enable fast mode by default for supported models
- `CHATGPT_LOCAL_CLIENT_ID`: OAuth client id override (rarely needed)
- `CHATGPT_LOCAL_EXPOSE_REASONING_MODELS`: `true|false` to add reasoning model variants to `/v1/models`
- `CHATGPT_LOCAL_ENABLE_WEB_SEARCH`: `true|false` to enable default web search tool

## Logs
Set `VERBOSE=true` to include extra logging for troubleshooting upstream or chat app requests. Please include and use these logs when submitting bug reports.

## API Key Example

With `data/security/api_tokens.txt` populated, clients must send:

```
curl -s http://127.0.0.1:9099/v1/models \
  -H 'Authorization: Bearer replace-me'
```

For Docker or `docker compose`, use a file such as `data/security/api_tokens.txt` in the repo root:

```text
# one token per line
replace-me
another-token
```

The token file is re-read on each request, so adding or removing tokens takes effect without restarting the container. You only need `CHATMOCK_API_KEY_FILE` if you want a non-default location.

The `data/` folder is bind-mounted into the container at `/app/data`, so both the token file and the blacklist persist across container restarts by default.

## Test

```
curl -s http://127.0.0.1:9099/v1/chat/completions \
   -H 'Content-Type: application/json' \
   -d '{"model":"gpt-5-codex","messages":[{"role":"user","content":"Hello world!"}]}' | jq .
```
