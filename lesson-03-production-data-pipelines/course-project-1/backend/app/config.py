from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://dc_user:dc_pass@db:5432/distribution_center"
    REDIS_URL: str = "redis://redis:6379/0"
    OPENAI_API_KEY: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
