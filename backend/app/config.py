from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # API
    API_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Telegram
    TELEGRAM_BOT_TOKEN: str
    ADMIN_USER_IDS: str = ""

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # TON
    TON_WALLET_ADDRESS: str
    TON_NETWORK: str = "mainnet"

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
