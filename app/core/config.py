"""
Application configuration management using Pydantic Settings.
"""
import os
from typing import List, Optional
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "GenAI Coach API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = False

    # Database
    DATABASE_URL: Optional[str] = None
    DB_ECHO: bool = False

    # Security
    SECRET_KEY: Optional[str] = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:8081"]
    CORS_ALLOW_CREDENTIALS: bool = True

    # AWS S3
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    AWS_ENDPOINT_URL: Optional[str] = None
    S3_BUCKET_NAME: Optional[str] = None
    S3_PRESIGNED_URL_EXPIRATION: int = 3600

    # AI Services - OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_WHISPER_MODEL: str = "whisper-1"

    # AI Services - Groq
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # LangSmith (Observability)
    LANGSMITH_TRACING: bool = False
    LANGSMITH_ENDPOINT: Optional[str] = None
    LANGSMITH_API_KEY: Optional[str] = None
    LANGSMITH_PROJECT: str = "genai-mock-interview"

    # Third-party AI Services
    LIVEKIT_API_KEY: Optional[str] = None
    LIVEKIT_API_SECRET: Optional[str] = None
    LIVEKIT_URL: Optional[str] = None
    CARTESIA_API_KEY: Optional[str] = None
    MURF_API_KEY: Optional[str] = None

    # Search Services (for RAG enhancement)
    EXA_API_KEY: Optional[str] = None
    SERPER_API_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None

    # Vector Database
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Redis (Optional)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Logging
    LOG_LEVEL: str = "INFO"

    # Sentry
    SENTRY_DSN: str = ""
    SENTRY_ENVIRONMENT: str = "production"
    SENTRY_TRACES_SAMPLE_RATE: float = 1.0
    SENTRY_PROFILES_SAMPLE_RATE: float = 1.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

    @model_validator(mode="after")
    def set_database_url(self):
        """Set DATABASE_URL from Railway's MYSQL_URL if not provided."""
        if not self.DATABASE_URL:
            mysql_url = os.getenv("MYSQL_URL")
            if mysql_url:
                # Convert mysql:// to mysql+aiomysql://
                self.DATABASE_URL = mysql_url.replace("mysql://", "mysql+aiomysql://")
            else:
                raise ValueError("DATABASE_URL or MYSQL_URL must be set")
        return self

    @model_validator(mode="after")
    def validate_required_fields(self):
        """Validate required fields are set."""
        if not self.SECRET_KEY:
            raise ValueError("SECRET_KEY environment variable is required")
        # OPENAI_API_KEY is optional - AI features will be disabled without it
        # AWS credentials are optional - S3 features will be disabled without them
        return self

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL for Alembic."""
        return self.DATABASE_URL.replace("+aiomysql", "+pymysql") if self.DATABASE_URL else ""


settings = Settings()
