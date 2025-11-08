from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings"""

    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN: str
    ADMIN_USER_IDS: str  # Comma-separated list of admin user IDs

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

    # Withdrawal Settings
    MIN_WITHDRAWAL_STARS: int = 1000
    MIN_WITHDRAWAL_RUB: int = 100

    # Privacy Settings
    SHOW_USERNAMES: bool = True

    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    def get_admin_ids(self) -> List[int]:
        """
        Parse and return list of admin user IDs from comma-separated string

        Returns:
            List of admin user IDs as integers
        """
        try:
            return [int(uid.strip()) for uid in self.ADMIN_USER_IDS.split(",") if uid.strip()]
        except (ValueError, AttributeError):
            return []

    def is_admin(self, user_id: int) -> bool:
        """
        Check if user ID is in the admin list

        Args:
            user_id: Telegram user ID to check

        Returns:
            True if user is admin, False otherwise
        """
        return user_id in self.get_admin_ids()


settings = Settings()
