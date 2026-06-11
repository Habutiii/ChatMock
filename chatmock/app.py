from __future__ import annotations

from flask import Flask, jsonify, request as flask_request
from flask_sock import Sock

from .config import (
    BASE_INSTRUCTIONS,
    GPT5_CODEX_INSTRUCTIONS,
    get_auth_blacklist_attempts,
    get_auth_blacklist_path,
    get_auth_window_seconds,
    get_server_api_key_file,
)
from .http import build_cors_headers, json_error
from .routes_openai import openai_bp
from .routes_ollama import ollama_bp
from .security import ApiSecurityManager, get_bearer_token, get_request_ip
from .websocket_routes import register_websocket_routes


def create_app(
    verbose: bool = False,
    verbose_obfuscation: bool = False,
    reasoning_effort: str = "medium",
    reasoning_summary: str = "auto",
    reasoning_compat: str = "think-tags",
    fast_mode: bool = False,
    debug_model: str | None = None,
    expose_reasoning_models: bool = False,
    default_web_search: bool = False,
) -> Flask:
    app = Flask(__name__)

    app.config.update(
        VERBOSE=bool(verbose),
        VERBOSE_OBFUSCATION=bool(verbose_obfuscation),
        REASONING_EFFORT=reasoning_effort,
        REASONING_SUMMARY=reasoning_summary,
        REASONING_COMPAT=reasoning_compat,
        FAST_MODE=bool(fast_mode),
        DEBUG_MODEL=debug_model,
        BASE_INSTRUCTIONS=BASE_INSTRUCTIONS,
        GPT5_CODEX_INSTRUCTIONS=GPT5_CODEX_INSTRUCTIONS,
        EXPOSE_REASONING_MODELS=bool(expose_reasoning_models),
        DEFAULT_WEB_SEARCH=bool(default_web_search),
    )
    app.config["API_SECURITY"] = ApiSecurityManager(
        (),
        api_key_file=get_server_api_key_file(),
        blacklist_attempts=get_auth_blacklist_attempts(),
        window_seconds=get_auth_window_seconds(),
        blacklist_path=get_auth_blacklist_path(),
    )

    @app.get("/")
    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.before_request
    def _enforce_api_key():
        if app.config.get("API_SECURITY") is None:
            return None
        if flask_request.method == "OPTIONS":
            return None
        if flask_request.path in ("/", "/health"):
            return None
        security = app.config["API_SECURITY"]
        client_ip = get_request_ip(flask_request.headers, flask_request.remote_addr)
        decision = security.authorize(get_bearer_token(flask_request.headers), client_ip)
        if decision.allowed:
            return None
        return json_error(decision.message, status=decision.status_code)

    @app.after_request
    def _cors(resp):
        for k, v in build_cors_headers().items():
            resp.headers.setdefault(k, v)
        return resp

    app.register_blueprint(openai_bp)
    app.register_blueprint(ollama_bp)
    sock = Sock(app)
    register_websocket_routes(sock)

    return app
