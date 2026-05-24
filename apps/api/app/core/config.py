from pydantic_settings import BaseSettings 

class Settings(BaseSettings): 
    database_url: str
    supabase_url: str 
    supabase_anon_key: str
    gemini_api_key: str
    ollama_enabled: bool = False
    ollama_host: str = "http://localhost:11434"
    ollama_embedding_model: str = "nomic-embed-text"
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    class Config: 
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
