from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database (PostgreSQL — metadata only, no vectors)
    DATABASE_URL: str = "postgresql+asyncpg://intel:intel_pass@localhost:5432/intel_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"

    # Local LLM (Phi-3 via Ollama)
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "phi3"

    # ChromaDB — set CHROMA_HOST to connect via HTTP (Docker mode)
    # Leave blank to use embedded mode (local dev)
    CHROMA_HOST: str = ""
    CHROMA_PORT: int = 8000

    # Embedding model (runs locally)
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_DIM: int = 768

    # Optional external API keys (all optional — demo data used if blank)
    BRAVE_API_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None
    FIRECRAWL_API_KEY: Optional[str] = None
    REDDIT_CLIENT_ID: Optional[str] = None
    REDDIT_CLIENT_SECRET: Optional[str] = None
    GITHUB_TOKEN: Optional[str] = None
    NEWSAPI_KEY: Optional[str] = None
    LINKEDIN_TOKEN: Optional[str] = None
    LANGFUSE_PUBLIC_KEY: Optional[str] = None
    LANGFUSE_SECRET_KEY: Optional[str] = None

    # Report output path
    REPORTS_DIR: str = "/tmp/reports"

    class Config:
        env_file = ".env"


settings = Settings()
