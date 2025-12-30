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

    # YooKassa Configuration (for RUB payments) - DEPRECATED
    YOOKASSA_SHOP_ID: Optional[str] = None
    YOOKASSA_SECRET_KEY: Optional[str] = None

    # TON Configuration
    TON_CENTER_API_KEY: str  # API key for TON Console (https://tonconsole.com - provides tonapi.io access)
    TON_WALLET_ADDRESS: str  # Bot's TON wallet address for receiving payments
    TON_WALLET_MNEMONIC: str  # Bot's wallet mnemonic for sending payouts (keep secure!)
    TON_NETWORK: str = "mainnet"  # "mainnet" or "testnet"

    # TON Connect Configuration
    TON_CONNECT_MANIFEST_URL: str  # URL to tonconnect-manifest.json file (must be publicly accessible)

    # Random.org API
    RANDOM_ORG_API_KEY: str

    # Bot Settings
    MIN_PARTICIPANTS: int = 10
    STARS_ENTRY_FEE: int = 10
    RUB_ENTRY_FEE: int = 100
    TON_ENTRY_FEE: float = 0.5  # Entry fee in TON (recommended: 0.5 TON)
    STARS_COMMISSION_PERCENT: int = 20
    RUB_COMMISSION_PERCENT: int = 15
    TON_COMMISSION_PERCENT: int = 12  # Lower commission for TON (12%)

    # Reserve Settings
    STARS_RESERVE_MIN: int = 3000
    STARS_RESERVE_TARGET: int = 5000
    TON_RESERVE_MIN: float = 10.0  # Minimum TON reserve (10 TON)
    TON_RESERVE_TARGET: float = 20.0  # Target TON reserve (20 TON)

    # Withdrawal Settings
    MIN_WITHDRAWAL_STARS: int = 1  # Changed to 1 to allow any amount
    MIN_WITHDRAWAL_RUB: int = 100
    MIN_WITHDRAWAL_TON: float = 0.1  # Minimum TON withdrawal (0.1 TON)

    # Currency Settings
    STARS_ONLY: bool = False  # DEPRECATED - Disable RUB payments, only use Telegram Stars
    TON_ONLY: bool = True  # Enable ONLY TON payments (disable Stars and RUB)

    # Transaction Monitoring
    TON_TRANSACTION_CHECK_INTERVAL: int = 15  # Check for new transactions every 15 seconds
    TON_TRANSACTION_CONFIRMATIONS: int = 1  # Number of confirmations required

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
