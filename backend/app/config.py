from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    app_host: str
    app_port: int
    db_host: str
    db_port: int
    db_user: str
    db_pass: str
    db_name: str
    enable_simulation: bool
    sim_metrics_every: float
    sim_insights_every: float
    allowed_origins: str
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    deepseek_embed_base_url: str
    deepseek_embed_model: str
    feishu_bot_enabled: bool
    feishu_base_url: str
    feishu_app_id: str
    feishu_app_secret: str
    feishu_verification_token: str
    feishu_encrypt_key: str
    feishu_max_doc_chars: int
    feishu_kb_sources: str
    feishu_kb_enabled: bool
    feishu_kb_collection: str
    feishu_kb_persist_dir: str
    feishu_kb_embed_model: str
    feishu_kb_refresh_every: float
    feishu_kb_chunk_size: int
    feishu_kb_chunk_overlap: int
    feishu_kb_top_k: int
    feishu_kb_min_score: float
    feishu_kb_max_doc_chars: int


def _load_env() -> None:
    cwd = Path.cwd()
    for path in [cwd, *cwd.parents]:
        env_path = path / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            return
    raise RuntimeError(".env file not found (searched upward from current directory)")


def _get_env(key: str, default: Optional[str] = None) -> str:
    value = os.getenv(key)
    if value is None or value == "":
        if default is None:
            return ""
        return default
    return value


def _parse_duration(value: str, fallback_seconds: float) -> float:
    if not value:
        return fallback_seconds
    text = value.strip().lower()
    if text.isdigit():
        return float(text)
    multipliers = {
        "ms": 0.001,
        "s": 1.0,
        "m": 60.0,
        "h": 3600.0,
    }
    for suffix, multiplier in multipliers.items():
        if text.endswith(suffix):
            number = text[: -len(suffix)].strip()
            try:
                return float(number) * multiplier
            except ValueError:
                return fallback_seconds
    return fallback_seconds


def load_settings() -> Settings:
    _load_env()

    app_port = int(_get_env("APP_PORT", "8080"))

    settings = Settings(
        app_host="0.0.0.0",
        app_port=app_port,
        db_host=_get_env("DB_HOST", "127.0.0.1"),
        db_port=int(_get_env("DB_PORT", "3306")),
        db_user=_get_env("DB_USER", "root"),
        db_pass=_get_env("DB_PASS", "123456"),
        db_name=_get_env("DB_NAME", "dashboard"),
        enable_simulation=_get_env("ENABLE_SIMULATION", "true").lower() == "true",
        sim_metrics_every=_parse_duration(_get_env("SIM_METRICS_EVERY", "1s"), 1.0),
        sim_insights_every=_parse_duration(_get_env("SIM_INSIGHTS_EVERY", "5s"), 5.0),
        allowed_origins=_get_env("ALLOWED_ORIGINS", "*"),
        deepseek_api_key=_get_env("DEEPSEEK_API_KEY", ""),
        deepseek_base_url=_get_env("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        deepseek_model=_get_env("DEEPSEEK_MODEL", "deepseek-chat"),
        deepseek_embed_base_url=_get_env("DEEPSEEK_EMBED_BASE_URL", ""),
        deepseek_embed_model=_get_env("DEEPSEEK_EMBED_MODEL", "deepseek-embedding"),
        feishu_bot_enabled=_get_env("FEISHU_BOT_ENABLED", "false").lower() == "true",
        feishu_base_url=_get_env("FEISHU_BASE_URL", "https://open.feishu.cn"),
        feishu_app_id=_get_env("FEISHU_APP_ID", ""),
        feishu_app_secret=_get_env("FEISHU_APP_SECRET", ""),
        feishu_verification_token=_get_env("FEISHU_VERIFICATION_TOKEN", ""),
        feishu_encrypt_key=_get_env("FEISHU_ENCRYPT_KEY", ""),
        feishu_max_doc_chars=int(_get_env("FEISHU_MAX_DOC_CHARS", "8000")),
        feishu_kb_sources=_get_env("FEISHU_KB_SOURCES", ""),
        feishu_kb_enabled=_get_env("FEISHU_KB_ENABLED", "true").lower() == "true",
        feishu_kb_collection=_get_env("FEISHU_KB_COLLECTION", "feishu_docs"),
        feishu_kb_persist_dir=_get_env("FEISHU_KB_PERSIST_DIR", "data/chroma"),
        feishu_kb_embed_model=_get_env(
            "FEISHU_KB_EMBED_MODEL", "BAAI/bge-small-zh-v1.5"
        ),
        feishu_kb_refresh_every=_parse_duration(
            _get_env("FEISHU_KB_REFRESH_EVERY", "5m"), 300.0
        ),
        feishu_kb_chunk_size=int(_get_env("FEISHU_KB_CHUNK_SIZE", "900")),
        feishu_kb_chunk_overlap=int(_get_env("FEISHU_KB_CHUNK_OVERLAP", "120")),
        feishu_kb_top_k=int(_get_env("FEISHU_KB_TOP_K", "6")),
        feishu_kb_min_score=float(_get_env("FEISHU_KB_MIN_SCORE", "0.2")),
        feishu_kb_max_doc_chars=int(_get_env("FEISHU_KB_MAX_DOC_CHARS", "12000")),
    )

    if not settings.deepseek_embed_base_url:
        object.__setattr__(settings, "deepseek_embed_base_url", settings.deepseek_base_url)

    if not settings.deepseek_api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is required")

    if settings.feishu_bot_enabled:
        if not settings.feishu_app_id or not settings.feishu_app_secret:
            raise RuntimeError("FEISHU_APP_ID/FEISHU_APP_SECRET are required when bot enabled")

    if settings.feishu_kb_sources or settings.feishu_kb_enabled:
        if not settings.feishu_app_id or not settings.feishu_app_secret:
            raise RuntimeError("FEISHU_APP_ID/FEISHU_APP_SECRET are required for KB sources")

    return settings

