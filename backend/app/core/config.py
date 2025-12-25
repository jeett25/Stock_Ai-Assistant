from pydantic_settings import BaseSettings , SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # App Info
    APP_NAME: str = "Stock Market AI Assistant"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str
    
    # API Keys (will add later)
    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.1-8b-instant"  # Fast and free
    # OPENAI_API_KEY: str = ""
    # LLM_MODEL: str = "gpt-4o-mini"
    NEWS_API_KEY: str = ""
    
    # # Embedding Settings
    # EMBEDDING_MODEL: str = "text-embedding-3-small"
    # EMBEDDING_DIMENSION: int = 1536
    # CHUNK_SIZE: int = 500
    # CHUNK_OVERLAP: int = 50
    
    
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384  # CHANGED from 1536
    
    # Chunking settings (unchanged)
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    
    # LLM Settings
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2048
    # MAX_CONTEXT_TOKENS: int = 8000
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra='ignore'
    )




@lru_cache()
def get_settings() -> Settings:
    """
    Create cached settings instance.
    Using lru_cache ensures we only load settings once.
    """
    return Settings()

settings = get_settings()