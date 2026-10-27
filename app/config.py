import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    LLM_MODEL: str = "llama-3.1-8b-instant"  # Updated to a universally available Groq model
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

settings = Settings()