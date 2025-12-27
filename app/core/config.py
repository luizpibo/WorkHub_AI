"""Application configuration using Pydantic Settings"""
from pydantic import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://workhub:workhub123@localhost:5432/workhub_db"
    
    # OpenAI / Gemini
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_MODEL: str = "gemini-2.5-flash"
    LLM_PROVIDER: str = "openai"  # openai ou google
    
    # App
    APP_ENV: str = "development"
    APP_NAME: str = "WorkHub AI Sales"
    API_V1_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"
    AUTO_SEED: bool = True  # Auto-seed database on startup
    
    # Security
    API_KEY_HEADER: str = "X-API-Key"
    
    # Admin
    ADMIN_KEYWORDS: list = ["admin", "ADMIN", "administrador", "Administrador"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

