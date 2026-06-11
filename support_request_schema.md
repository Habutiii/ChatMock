# Supported Request Schemas

This document describes the client request formats that `ChatMock` currently supports reliably.

It is intentionally practical, not aspirational. If a format is accepted by the route but not mapped correctly upstream, it is listed as not reliably supported.

## Base URLs

- OpenAI-compatible: `http://<host>:9099/v1`
- Ollama-compatible: `http://<host>:9099/api`

## Authentication

All non-health routes can require:

```http
Authorization: Bearer <token>
```

Health routes:

- `GET /`
- `GET /health`

## OpenAI-Compatible Endpoints

### `GET /v1/models`

Supported request:

```http
GET /v1/models
Authorization: Bearer <token>
```

### `POST /v1/chat/completions`

This endpoint is reliably supported for normal text chat, image input, streaming, and OpenAI-style tool declarations.

### Minimal text chat

```json
{
  "model": "gpt-5.4-mini",
  "messages": [
    {
      "role": "user",
      "content": "Hello"
    }
  ]
}
```

### Streaming text chat

```json
{
  "model": "gpt-5.4-mini",
  "stream": true,
  "messages": [
    {
      "role": "user",
      "content": "Hello"
    }
  ]
}
```

### Vision / image input

```json
{
  "model": "gpt-5.4-mini",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "Describe this image."
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/png;base64,..."
          }
        }
      ]
    }
  ]
}
```

### Tool calling

```json
{
  "model": "gpt-5.4-mini",
  "messages": [
    {
      "role": "user",
      "content": "What is the weather in Singapore?"
    }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get current weather",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string"
            }
          },
          "required": ["location"]
        }
      }
    }
  ],
  "tool_choice": "auto",
  "parallel_tool_calls": false
}
```

### Extra compatibility fields currently handled

These fields are accepted and used by `ChatMock`:

- `model`
- `messages`
- `stream`
- `stream_options.include_usage`
- `tools`
- `tool_choice`
- `parallel_tool_calls`
- `prompt`
- `input`
- `reasoning`
- `fast_mode`
- `service_tier`
- `responses_tools`
- `responses_tool_choice`

### Not reliably supported on `/v1/chat/completions`

The following OpenAI-style schema is not correctly implemented end-to-end yet:

```json
{
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "structured_output",
      "strict": true,
      "schema": {}
    }
  }
}
```

Reason:

- `ChatMock` currently accepts this field from clients, but does not correctly translate it into the upstream request format that would enforce strict structured output.
- As a result, you may receive plain text or mixed text instead of guaranteed schema-constrained JSON.

Temporary guidance:

- Do use `/v1/chat/completions` for text, image, streaming, and tools.
- Do not depend on strict `response_format.json_schema` compatibility yet.

### `POST /v1/responses`

This endpoint is closer to the upstream Responses API and is the better fit for advanced request features.

Supported minimal request:

```json
{
  "model": "gpt-5.4-mini",
  "input": "Hello"
}
```

Also supported:

- `input` as a string
- `input` as a Responses-style message array
- `reasoning`
- `tools`
- `tool_choice`
- `service_tier`
- `stream`

### `GET /v1/responses` WebSocket

Supported route:

- WebSocket endpoint: `/v1/responses`

Expected first message:

```json
{
  "type": "response.create",
  "model": "gpt-5.4-mini",
  "input": "Hello"
}
```

Bearer token auth is checked during the WebSocket request handshake.

## Ollama-Compatible Endpoints

### `GET /api/tags`

Supported request:

```http
GET /api/tags
Authorization: Bearer <token>
```

### `POST /api/chat`

Supported minimal request:

```json
{
  "model": "gpt-5.4-mini",
  "messages": [
    {
      "role": "user",
      "content": "Hello"
    }
  ],
  "stream": false
}
```

Also supported:

- `stream: true`
- image input in Ollama-style message/image fields
- tool declarations in normalized function-tool form

## Summary

Reliable today:

- `GET /health`
- `GET /v1/models`
- `POST /v1/chat/completions` for normal text chat
- `POST /v1/chat/completions` for image input
- `POST /v1/chat/completions` for streaming
- `POST /v1/chat/completions` for tool calling
- `POST /v1/responses`
- `GET /api/tags`
- `POST /api/chat`

Not reliably supported yet:

- strict structured output on `/v1/chat/completions` via `response_format.json_schema`
