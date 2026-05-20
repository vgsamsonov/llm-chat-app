from pydantic_settings import BaseSettings
from functools import lru_cache
import redis.asyncio as aioredis
from functools import lru_cache

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    GITHUB_CLIENT_ID: str
    GITHUB_CLIENT_SECRET: str
    GITHUB_REDIRECT_URI: str = "http://localhost:8000/api/auth/github/callback"
    LLM_MODEL_PATH: str = "./model.gguf"
    LLM_MAX_TOKENS: int = 512
    LLM_TEMPERATURE: float = 0.7
    FRONTEND_URL: str = "http://localhost:5173"

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Add Redis connection factory
@lru_cache()
def get_redis_client():
    settings = get_settings()
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)