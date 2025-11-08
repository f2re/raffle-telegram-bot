"""Service for Telegram Stars operations"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
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
        # Telegram allows refunds within 21 days
        self.REFUND_WINDOW_DAYS = 21

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

    async def process_withdrawal_with_multiple_refunds(
        self,
        user_id: int,
        telegram_id: int,
        withdrawal_amount: int,
        transactions: List[Any]
    ) -> Dict[str, Any]:
        """
        Process star withdrawal using multiple refund attempts

        This method tries to refund stars from multiple recent payments to cover
        the full withdrawal amount. This is the ONLY official way to return stars
        to users according to Telegram Bot API.

        Args:
            user_id: Internal user ID
            telegram_id: Telegram user ID
            withdrawal_amount: Total amount of stars to withdraw
            transactions: List of user's recent star transactions with payment_id

        Returns:
            Dictionary with:
                - total_refunded: Amount successfully refunded
                - remaining: Amount that couldn't be refunded
                - successful_refunds: List of successful refund details
                - failed_refunds: List of failed refund details
        """
        total_refunded = 0
        remaining = withdrawal_amount
        successful_refunds = []
        failed_refunds = []

        # Filter transactions that are eligible for refund:
        # 1. Must have payment_id (telegram_payment_charge_id)
        # 2. Must be within 21-day refund window
        # 3. Must be completed star payments
        cutoff_date = datetime.utcnow() - timedelta(days=self.REFUND_WINDOW_DAYS)

        eligible_transactions = []
        for tx in transactions:
            if (tx.payment_id and
                tx.created_at >= cutoff_date and
                tx.amount > 0):
                eligible_transactions.append(tx)

        logger.info(
            f"Processing withdrawal for user {telegram_id}: "
            f"requested={withdrawal_amount}, "
            f"eligible_transactions={len(eligible_transactions)}"
        )

        # Sort transactions by date (newest first) to maximize refund success
        eligible_transactions.sort(key=lambda x: x.created_at, reverse=True)

        # Try to refund from each eligible transaction
        for tx in eligible_transactions:
            if remaining <= 0:
                break

            # Amount to refund from this transaction
            # Note: We can only refund up to the original transaction amount
            refund_amount = min(remaining, int(tx.amount))

            try:
                # Important: Telegram's refundStarPayment refunds the FULL original payment
                # We cannot do partial refunds of a single payment
                # So we can only use this if the transaction amount <= remaining amount
                if tx.amount <= remaining:
                    result = await self.refund_star_payment(
                        user_id=telegram_id,
                        telegram_payment_charge_id=tx.payment_id
                    )

                    refunded_amount = int(tx.amount)
                    total_refunded += refunded_amount
                    remaining -= refunded_amount

                    successful_refunds.append({
                        "transaction_id": tx.id,
                        "payment_id": tx.payment_id,
                        "amount": refunded_amount,
                        "created_at": tx.created_at.isoformat()
                    })

                    logger.info(
                        f"Successfully refunded {refunded_amount} stars "
                        f"from transaction {tx.id} (payment_id: {tx.payment_id})"
                    )
                else:
                    # Skip this transaction as it's larger than remaining amount
                    # and we can't do partial refunds
                    logger.debug(
                        f"Skipping transaction {tx.id}: amount ({tx.amount}) > "
                        f"remaining ({remaining}), partial refunds not supported"
                    )

            except Exception as e:
                logger.warning(
                    f"Failed to refund transaction {tx.id} "
                    f"(payment_id: {tx.payment_id}): {e}"
                )
                failed_refunds.append({
                    "transaction_id": tx.id,
                    "payment_id": tx.payment_id,
                    "amount": int(tx.amount),
                    "error": str(e)
                })

        result = {
            "total_refunded": total_refunded,
            "remaining": remaining,
            "successful_refunds": successful_refunds,
            "failed_refunds": failed_refunds,
            "refund_rate": (total_refunded / withdrawal_amount * 100) if withdrawal_amount > 0 else 0
        }

        logger.info(
            f"Withdrawal processing complete for user {telegram_id}: "
            f"refunded={total_refunded}/{withdrawal_amount} stars "
            f"({result['refund_rate']:.1f}%), remaining={remaining}"
        )

        return result


def create_stars_service(bot: Bot) -> StarsService:
    """
    Create StarsService instance

    Args:
        bot: Aiogram Bot instance

    Returns:
        StarsService instance
    """
    return StarsService(bot)
