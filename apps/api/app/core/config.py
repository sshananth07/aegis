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

    def validate_required(self):
        missing = []
        if not self.database_url:
            missing.append("DATABASE_URL")
        if not self.gemini_api_key:
            missing.append("GEMINI_API_KEY")
        if not self.supabase_url:
            missing.append("SUPABASE_URL")
        if not self.supabase_anon_key:
            missing.append("SUPABASE_ANON_KEY")
        if missing:
            raise RuntimeError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

settings = Settings() 

