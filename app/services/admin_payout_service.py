"""
Admin Payout Service

Handles raffle winner payouts via admin using invoice links.
Admin receives invoice link, pays winner, and confirms payout.
"""
from typing import Optional
from aiogram import Bot
from aiogram.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger

from app.database import crud
from app.database.session import get_session
from app.database.models import CurrencyType, PayoutStatus


class AdminPayoutService:
    """Service for handling payouts via administrator"""

    def __init__(self, bot: Bot):
        self.bot = bot

    async def create_payout_invoice_link(
        self,
        winner_id: int,
        amount: float,
        raffle_id: int,
        winner_username: Optional[str] = None,
        currency: CurrencyType = CurrencyType.STARS,
    ) -> str:
        """
        Create invoice link for admin to pay winner

        Args:
            winner_id: Winner's telegram ID
            amount: Prize amount
            raffle_id: Raffle ID
            winner_username: Winner's username (optional)
            currency: Payment currency (STARS or RUB)

        Returns:
            Invoice link URL
        """
        try:
            # Convert amount to integer for stars
            if currency == CurrencyType.STARS:
                amount = int(amount)

            # Create payload with raffle and winner info
            payload = f"payout_{raffle_id}_{winner_id}"

            # Format description
            winner_mention = f"@{winner_username}" if winner_username else f"ID {winner_id}"
            description = (
                f"Приз за победу в розыгрыше #{raffle_id}\n"
                f"Победитель: {winner_mention}"
            )

            # Determine currency for invoice
            if currency == CurrencyType.STARS:
                invoice_currency = "XTR"  # Telegram Stars
                price_label = f"Приз: {amount} ⭐"
            else:
                invoice_currency = "RUB"
                price_label = f"Приз: {amount} ₽"

            # Create invoice link
            invoice_link = await self.bot.create_invoice_link(
                title=f"Приз за розыгрыш #{raffle_id}",
                description=description,
                payload=payload,
                provider_token="",  # Empty for Telegram Stars
                currency=invoice_currency,
                prices=[
                    LabeledPrice(
                        label=price_label,
                        amount=int(amount) if currency == CurrencyType.STARS else int(amount * 100)
                        # Telegram expects price in smallest units (kopeks for RUB)
                    )
                ]
            )

            logger.info(
                f"Created payout invoice link for raffle {raffle_id}, "
                f"winner {winner_id}, amount: {amount} {currency.value}"
            )

            return invoice_link

        except Exception as e:
            logger.error(f"Failed to create invoice link: {e}", exc_info=True)
            raise

    async def send_payout_request_to_admin(
        self,
        admin_id: int,
        winner_id: int,
        winner_username: Optional[str],
        winner_name: str,
        amount: float,
        raffle_id: int,
        currency: CurrencyType,
    ):
        """
        Send payout request to administrator with invoice link

        Args:
            admin_id: Admin's telegram ID
            winner_id: Winner's telegram ID
            winner_username: Winner's username
            winner_name: Winner's display name
            amount: Prize amount
            raffle_id: Raffle ID
            currency: Payment currency
        """
        try:
            # Create invoice link
            invoice_link = await self.create_payout_invoice_link(
                winner_id=winner_id,
                amount=amount,
                raffle_id=raffle_id,
                winner_username=winner_username,
                currency=currency,
            )

            # Save payout request to database
            async with get_session() as session:
                # Get winner's database ID
                winner = await crud.get_user_by_telegram_id(session, winner_id)
                if not winner:
                    raise ValueError(f"Winner user {winner_id} not found in database")

                await crud.create_payout_request(
                    session,
                    raffle_id=raffle_id,
                    winner_id=winner.id,
                    amount=amount,
                    currency=currency,
                    invoice_link=invoice_link,
                )

            # Format currency display
            currency_symbol = "⭐" if currency == CurrencyType.STARS else "₽"
            amount_str = f"{int(amount)}" if currency == CurrencyType.STARS else f"{amount:.2f}"

            # Format admin message
            admin_message = (
                f"🎉 <b>ТРЕБУЕТСЯ ВЫПЛАТА ПРИЗА</b>\n\n"
                f"🏆 Розыгрыш: #{raffle_id}\n"
                f"👤 Победитель: {winner_name}"
            )

            if winner_username:
                admin_message += f" (@{winner_username})"

            admin_message += (
                f"\n💰 Сумма приза: {amount_str} {currency_symbol}\n\n"
                f"<b>Инструкция:</b>\n"
                f"1. Нажмите кнопку '💳 Оплатить приз'\n"
                f"2. Откроется платежное окно Telegram\n"
                f"3. Подтвердите отправку {amount_str} {currency_symbol} победителю\n"
                f"4. После оплаты нажмите '✅ Подтвердить выплату'\n\n"
                f"⚠️ Убедитесь, что на вашем балансе есть {amount_str} {currency_symbol}!"
            )

            # Create keyboard with action buttons
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💳 Оплатить приз",
                        url=invoice_link
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="✅ Подтвердить выплату",
                        callback_data=f"confirm_payout:{raffle_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Отклонить выплату",
                        callback_data=f"reject_payout:{raffle_id}"
                    )
                ]
            ])

            # Send to admin
            await self.bot.send_message(
                admin_id,
                admin_message,
                reply_markup=keyboard,
                parse_mode="HTML"
            )

            logger.info(
                f"Payout request sent to admin {admin_id} for raffle {raffle_id}"
            )

        except Exception as e:
            logger.error(f"Failed to send payout request: {e}", exc_info=True)
            raise

    async def notify_winner_payment_pending(
        self,
        winner_id: int,
        amount: float,
        raffle_id: int,
        currency: CurrencyType,
    ):
        """
        Notify winner that payout is pending admin confirmation

        Args:
            winner_id: Winner's telegram ID
            amount: Prize amount
            raffle_id: Raffle ID
            currency: Payment currency
        """
        try:
            currency_symbol = "⭐" if currency == CurrencyType.STARS else "₽"
            amount_str = f"{int(amount)}" if currency == CurrencyType.STARS else f"{amount:.2f}"

            message = (
                f"🎉 <b>Поздравляем с победой!</b>\n\n"
                f"Вы выиграли в розыгрыше #{raffle_id}!\n"
                f"💰 Ваш приз: {amount_str} {currency_symbol}\n\n"
                f"⏳ Выплата находится в обработке.\n"
                f"Администратор переведет средства в ближайшее время.\n"
                f"Обычно это занимает несколько минут.\n\n"
                f"Вы получите уведомление, как только средства поступят."
            )

            await self.bot.send_message(
                winner_id,
                message,
                parse_mode="HTML"
            )

            logger.info(f"Winner {winner_id} notified about pending payout")

        except Exception as e:
            logger.error(f"Failed to notify winner: {e}", exc_info=True)
            # Don't raise - this is not critical

    async def notify_winner_payment_completed(
        self,
        winner_id: int,
        amount: float,
        raffle_id: int,
        currency: CurrencyType,
    ):
        """
        Notify winner that payout has been completed

        Args:
            winner_id: Winner's telegram ID
            amount: Prize amount
            raffle_id: Raffle ID
            currency: Payment currency
        """
        try:
            currency_symbol = "⭐" if currency == CurrencyType.STARS else "₽"
            amount_str = f"{int(amount)}" if currency == CurrencyType.STARS else f"{amount:.2f}"

            message = (
                f"✅ <b>Приз получен!</b>\n\n"
                f"Вам было отправлено {amount_str} {currency_symbol}.\n"
            )

            if currency == CurrencyType.STARS:
                message += "Проверьте ваш баланс Telegram Stars!\n\n"
            else:
                message += "Средства поступят на указанный счет в течение 1-3 рабочих дней.\n\n"

            message += "Спасибо за участие в розыгрыше! 🎉"

            await self.bot.send_message(
                winner_id,
                message,
                parse_mode="HTML"
            )

            logger.info(f"Winner {winner_id} notified about completed payout")

        except Exception as e:
            logger.error(f"Failed to notify winner: {e}", exc_info=True)
            # Don't raise - this is not critical


def create_admin_payout_service(bot: Bot) -> AdminPayoutService:
    """Factory function to create AdminPayoutService instance"""
    return AdminPayoutService(bot)
