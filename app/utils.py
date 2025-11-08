"""Utility functions for the bot"""
from typing import Optional
from app.config import settings
from app.database.models import User, CurrencyType


def format_user_display_name(
    user: User,
    current_user_id: Optional[int] = None,
    show_username: bool = None
) -> str:
    """
    Format user display name based on privacy settings.

    Args:
        user: User object to format
        current_user_id: ID of the current user viewing the name (optional)
        show_username: Override for SHOW_USERNAMES setting (optional)

    Returns:
        Formatted user display name
    """
    if show_username is None:
        show_username = settings.SHOW_USERNAMES

    # Build display name
    display_name = user.first_name or "Пользователь"

    if user.last_name:
        display_name += f" {user.last_name}"

    # Add username only if:
    # 1. SHOW_USERNAMES is enabled OR
    # 2. This is the current user viewing their own name
    if show_username or (current_user_id and user.id == current_user_id):
        if user.username:
            display_name += f" (@{user.username})"

    return display_name


def round_rub_amount(amount: float) -> int:
    """
    Round RUB amount to whole rubles.

    Args:
        amount: Amount in rubles (can be float)

    Returns:
        Rounded amount as integer
    """
    return int(round(amount))


def format_currency_amount(amount: float, currency: CurrencyType) -> str:
    """
    Format currency amount for display.

    Args:
        amount: Amount to format
        currency: Currency type (STARS or RUB)

    Returns:
        Formatted string with amount and currency
    """
    if currency == CurrencyType.STARS:
        # Stars are always integers
        return f"{int(amount)} ⭐"
    else:
        # Rubles are rounded to integers
        return f"{round_rub_amount(amount)} ₽"


def validate_withdrawal_amount(amount: float, currency: CurrencyType) -> tuple[bool, Optional[str]]:
    """
    Validate withdrawal amount against minimum requirements.

    Args:
        amount: Requested withdrawal amount
        currency: Currency type (STARS or RUB)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if amount <= 0:
        return False, "Сумма должна быть больше нуля"

    if currency == CurrencyType.STARS:
        # Stars can be withdrawn in any amount (min 1 star)
        min_amount = settings.MIN_WITHDRAWAL_STARS
        if amount < min_amount:
            return False, f"Минимальная сумма для вывода: {min_amount} ⭐"
    else:
        # Rubles have a minimum withdrawal amount
        min_amount = settings.MIN_WITHDRAWAL_RUB
        if amount < min_amount:
            return False, f"Минимальная сумма для вывода: {min_amount} ₽"

    return True, None
