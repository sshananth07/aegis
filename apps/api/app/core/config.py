from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    database_url: str
    supabase_url: str
    supabase_anon_key: str
    supabase_jwt_secret: str = ""
    gemini_api_key: str
    cors_origins: str = "http://localhost:3000"
    ollama_enabled: bool = False
    ollama_host: str = "http://localhost:11434"

    class Config:
        env_file = ".env"

settings = Settings()

