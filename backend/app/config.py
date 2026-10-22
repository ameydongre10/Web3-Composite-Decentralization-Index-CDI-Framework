from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Web3 Composite Decentralization Index (CDI) Framework"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = (
        "Enterprise-grade, scientifically defensible platform for computing, "
        "monitoring, and forecasting Web3 and DAO decentralization metrics."
    )
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Database: Async SQLite for local dev/testing, Async PostgreSQL for production
    DATABASE_URL: str = "sqlite+aiosqlite:///./cdi_framework.db"

    # Security & API Auth
    SECRET_KEY: str = "cdi-production-secret-key-change-in-prod-2026"
    ADMIN_API_KEY: str = "cdi-admin-key-2026"
    RATE_LIMIT_PER_MINUTE: int = 120

    # External Web3 RPC and Indexers
    ETHEREUM_RPC_URL: str = "https://cloudflare-eth.com"
    GANACHE_RPC_URL: str = "http://127.0.0.1:8545"
    SNAPSHOT_GRAPHQL_URL: str = "https://hub.snapshot.org/graphql"
    COINGECKO_API_URL: str = "https://api.coingecko.com/api/v3"

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # Ingestion & Sync settings
    SYNC_INTERVAL_SECONDS: int = 60
    DEFAULT_LOOKBACK_DAYS: int = 90

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
