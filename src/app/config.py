"""Application configuration loaded from environment variables."""

import socket
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# ── Force IPv4 for all outgoing connections ──────────────────────────
# IPv6 connections are reset on some networks (ECONNRESET).
# Must be applied before any httpx / httpcore imports.
_original_getaddrinfo = socket.getaddrinfo


def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)


socket.getaddrinfo = _ipv4_getaddrinfo
# ──────────────────────────────────────────────────────────────────────


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Chat
    chat_api_key: str
    chat_base_url: str
    chat_model: str

    # Embedding
    embedding_api_key: str
    embedding_base_url: str
    embedding_model: str
    embedding_dimension: int

    # Pinecone
    pinecone_api_key: str
    pinecone_host_url: str
    pinecone_index_name: str

    # CORS
    cors_origin: str
    # PostgreSQL
    database_url: str

    # Auth0
    idp_domain: str
    idp_client_id: str
    idp_client_secret: str
    idp_audience: str

    # App
    app_env: str
    log_level: str
    rate_limit_per_account_per_min: int


@lru_cache
def get_settings() -> Settings:
    return Settings()
