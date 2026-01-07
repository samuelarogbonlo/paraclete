"""
Application configuration using Pydantic Settings.
"""
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator
import secrets


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
        case_sensitive=True,
    )

    # Application
    APP_NAME: str = "Paraclete API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False)
    API_V1_PREFIX: str = "/v1"

    # Server
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/paraclete"
    )
    DATABASE_POOL_SIZE: int = Field(default=20)
    DATABASE_MAX_OVERFLOW: int = Field(default=0)

    # Redis (optional - for production rate limiting and caching)
    REDIS_URL: Optional[str] = Field(default=None)

    # Security
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60)  # 1 hour
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:8080",
            "http://localhost",
        ]
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)
    CORS_ALLOW_METHODS: List[str] = Field(
        default=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    )
    CORS_ALLOW_HEADERS: List[str] = Field(
        default=[
            "Authorization",
            "Content-Type",
            "X-App-Version",
            "X-Platform",
            "X-Request-ID",
        ]
    )

    @validator("CORS_ORIGINS", pre=True)
    def validate_origins(cls, v):
        """Ensure wildcard CORS is not allowed in production."""
        if isinstance(v, str):
            v = [x.strip() for x in v.split(",")]
        # Allow wildcard only in DEBUG mode
        import os
        debug = os.getenv("DEBUG", "false").lower() == "true"
        if "*" in v and not debug:
            raise ValueError("Wildcard CORS not allowed in production (DEBUG=false)")
        return v

    # GitHub OAuth (for future implementation)
    GITHUB_CLIENT_ID: Optional[str] = Field(default=None)
    GITHUB_CLIENT_SECRET: Optional[str] = Field(default=None)
    GITHUB_REDIRECT_URI: Optional[str] = Field(default=None)

    # AI API Keys (for managed tier)
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None)
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    GOOGLE_API_KEY: Optional[str] = Field(default=None)

    # Voice Services
    DEEPGRAM_API_KEY: Optional[str] = Field(default=None)
    ELEVENLABS_API_KEY: Optional[str] = Field(default=None)

    # Firebase
    FIREBASE_PROJECT_ID: Optional[str] = Field(default=None)
    FIREBASE_PRIVATE_KEY: Optional[str] = Field(default=None)
    FIREBASE_CLIENT_EMAIL: Optional[str] = Field(default=None)

    # Infrastructure
    FLY_API_TOKEN: Optional[str] = Field(default=None)
    TAILSCALE_AUTH_KEY: Optional[str] = Field(default=None)

    # Redis (optional, for caching/sessions)
    REDIS_URL: Optional[str] = Field(default="redis://localhost:6379")

    # Encryption
    ENCRYPTION_KEY: Optional[str] = Field(default_factory=lambda: secrets.token_urlsafe(32))

    @validator("CORS_ORIGINS", pre=True)
    def parse_cors(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @validator("DATABASE_URL", pre=True)
    def fix_postgres_url(cls, v):
        # Fix for SQLAlchemy 2.0 requiring postgresql+asyncpg
        if v and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        if v and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v


# Create global settings instance
settings = Settings()