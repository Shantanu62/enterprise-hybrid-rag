from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "Enterprise Hybrid RAG Chatbot Suite"

    # LLM (Groq)
    GROQ_API_KEY: str = ""
    LLM_MODEL: str = "openai/gpt-oss-120b"

    # Embeddings (local, free)
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Redis (optional, only for semantic cache)
    REDIS_URL: str = "redis://localhost:6379"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()