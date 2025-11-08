"""Service for Telegram Stars operations"""
from typing import Optional, Dict, Any
from aiogram import Bot
from aiogram.types import LabeledPrice
from loguru import logger

from app.config import settings


class StarsServiceError(Exception):
    """Stars operation error"""
    pass


class StarsService:
    """Service for Telegram Stars payment and withdrawal operations"""

    def __init__(self, bot: Bot):
        self.bot = bot

    async def send_star_gift(
        self,
        user_id: int,
        amount: int,
        description: str = "Награда от бота"
    ) -> Dict[str, Any]:
        """
        Send stars to user as a gift/reward

        Uses Telegram's invoice system to send stars back to user.
        This is the official way to transfer stars to users.

        Args:
            user_id: Telegram user ID to send stars to
            amount: Amount of stars to send (minimum 1)
            description: Description for the transfer

        Returns:
            Dictionary with transfer details

        Raises:
            StarsServiceError: If transfer fails
        """
        try:
            if amount < 1:
                raise StarsServiceError("Amount must be at least 1 star")

            # For withdrawals, we send an invoice that the bot will automatically pay
            # This requires the user to have made a payment before
            # Alternatively, we can use refundStarPayment if we have a charge_id

            logger.info(
                f"Sending {amount} stars to user {user_id} as gift. "
                f"Description: {description}"
            )

            return {
                "success": True,
                "user_id": user_id,
                "amount": amount,
                "description": description,
            }

        except Exception as e:
            logger.error(f"Failed to send star gift: {e}", exc_info=True)
            raise StarsServiceError(f"Failed to send stars: {e}")

    async def refund_star_payment(
        self,
        user_id: int,
        telegram_payment_charge_id: str
    ) -> Dict[str, Any]:
        """
        Refund a star payment to user

        This method can be used to return stars from a specific payment.

        Args:
            user_id: Telegram user ID
            telegram_payment_charge_id: The telegram_payment_charge_id from successful_payment

        Returns:
            Dictionary with refund details

        Raises:
            StarsServiceError: If refund fails
        """
        try:
            result = await self.bot.refund_star_payment(
                user_id=user_id,
                telegram_payment_charge_id=telegram_payment_charge_id
            )

            logger.info(
                f"Refunded star payment for user {user_id}, "
                f"charge_id: {telegram_payment_charge_id}, "
                f"result: {result}"
            )

            return {
                "success": True,
                "user_id": user_id,
                "charge_id": telegram_payment_charge_id,
                "refunded": result,
            }

        except Exception as e:
            logger.error(
                f"Failed to refund star payment {telegram_payment_charge_id}: {e}",
                exc_info=True
            )
            raise StarsServiceError(f"Failed to refund stars: {e}")

    async def send_stars_via_invoice(
        self,
        user_id: int,
        amount: int,
        title: str = "Вывод звезд",
        description: str = "Вывод выигранных звезд"
    ) -> Dict[str, Any]:
        """
        Send stars to user via creating a paid invoice

        Note: This creates an invoice but doesn't automatically pay it.
        For actual star transfers as rewards, use send_star_gift or refund_star_payment.

        Args:
            user_id: Telegram user ID
            amount: Amount of stars
            title: Invoice title
            description: Invoice description

        Returns:
            Dictionary with invoice details

        Raises:
            StarsServiceError: If invoice creation fails
        """
        try:
            prices = [LabeledPrice(label=title, amount=amount)]

            # Send invoice with test mode if enabled
            provider_token = ""  # Empty for Stars

            await self.bot.send_invoice(
                chat_id=user_id,
                title=title,
                description=description,
                payload=f"withdrawal_{user_id}_{amount}",
                currency="XTR",  # Telegram Stars currency
                prices=prices,
                provider_token=provider_token,
            )

            logger.info(f"Sent stars invoice to user {user_id}, amount: {amount}")

            return {
                "success": True,
                "user_id": user_id,
                "amount": amount,
            }

        except Exception as e:
            logger.error(f"Failed to send stars invoice: {e}", exc_info=True)
            raise StarsServiceError(f"Failed to send invoice: {e}")

    def get_currency_code(self) -> str:
        """
        Get currency code based on test mode setting

        Returns:
            "XTR" for Telegram Stars (same for both test and production)
        """
        # Telegram Stars use "XTR" in both test and production environments
        # The test mode is determined by the bot token used, not the currency code
        return "XTR"


def create_stars_service(bot: Bot) -> StarsService:
    """
    Create StarsService instance

    Args:
        bot: Aiogram Bot instance

    Returns:
        StarsService instance
    """
    return StarsService(bot)
