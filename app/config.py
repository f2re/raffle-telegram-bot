from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""

    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN: str
    ADMIN_USER_ID: int

    # Database Configuration
    DATABASE_URL: str

    # Redis Configuration
    REDIS_URL: str = "redis://redis:6379/0"

    # YooKassa Configuration (for RUB payments)
    YOOKASSA_SHOP_ID: Optional[str] = None
    YOOKASSA_SECRET_KEY: Optional[str] = None

    # Random.org API
    RANDOM_ORG_API_KEY: str

    # Bot Settings
    MIN_PARTICIPANTS: int = 10
    STARS_ENTRY_FEE: int = 10
    RUB_ENTRY_FEE: int = 100
    STARS_COMMISSION_PERCENT: int = 20
    RUB_COMMISSION_PERCENT: int = 15

    # Reserve Settings
    STARS_RESERVE_MIN: int = 3000
    STARS_RESERVE_TARGET: int = 5000

    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
