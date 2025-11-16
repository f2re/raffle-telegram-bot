"""
TON Transaction Monitor

Background service that monitors incoming TON transactions
and processes raffle payments automatically
"""

import asyncio
from typing import Optional
from datetime import datetime

from aiogram import Bot
from loguru import logger

from app.config import settings
from app.database.session import get_session
from app.database import crud
from app.database.models import CurrencyType, TransactionType, TransactionStatus
from app.services.ton_service import ton_service, TonPaymentError
from app.handlers.raffle import execute_raffle


class TonTransactionMonitor:
    """
    Background service for monitoring TON transactions

    Runs continuously and checks for new incoming transactions
    every TON_TRANSACTION_CHECK_INTERVAL seconds
    """

    def __init__(self, bot: Bot):
        """
        Initialize monitor

        Args:
            bot: Telegram Bot instance
        """
        self.bot = bot
        self.running = False
        self.task: Optional[asyncio.Task] = None

    async def start(self):
        """Start monitoring task"""
        if self.running:
            logger.warning("TON monitor already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._monitor_loop())
        logger.info("TON transaction monitor started")

    async def stop(self):
        """Stop monitoring task"""
        if not self.running:
            return

        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

        logger.info("TON transaction monitor stopped")

    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                await self._check_transactions()
            except Exception as e:
                logger.error(f"Error in TON monitor loop: {e}", exc_info=True)

            # Wait before next check
            await asyncio.sleep(settings.TON_TRANSACTION_CHECK_INTERVAL)

    async def _check_transactions(self):
        """Check for new incoming transactions"""
        try:
            # Get incoming transactions
            transactions = await ton_service.check_incoming_transactions()

            if not transactions:
                logger.debug("No new transactions to process")
                return

            logger.info(f"Found {len(transactions)} new TON transactions")

            # Process each transaction
            for tx in transactions:
                await self._process_transaction(tx)

        except TonPaymentError as e:
            # Log error but continue monitoring (could be temporary network issue)
            logger.warning(f"TON payment error (will retry on next check): {e}")
        except Exception as e:
            # Log unexpected errors but continue monitoring
            logger.error(f"Unexpected error checking transactions (will retry on next check): {e}", exc_info=True)

    async def _process_transaction(self, tx: dict):
        """
        Process a single incoming transaction

        Args:
            tx: Transaction dictionary from ton_service
        """
        try:
            # Parse comment to extract raffle_id and user_id
            comment_data = ton_service.parse_payment_comment(tx["comment"])

            if not comment_data:
                logger.warning(
                    f"Invalid comment format: '{tx['comment']}' "
                    f"(tx: {tx['hash'][:8]}...)"
                )
                return

            raffle_id = comment_data["raffle_id"]
            user_id = comment_data["user_id"]

            async with get_session() as session:
                # Get raffle
                raffle = await crud.get_raffle_by_id(session, raffle_id)
                if not raffle:
                    logger.warning(f"Raffle {raffle_id} not found")
                    return

                # Verify raffle uses TON
                if raffle.entry_fee_type != CurrencyType.TON:
                    logger.warning(
                        f"Raffle {raffle_id} does not use TON "
                        f"(uses {raffle.entry_fee_type.value})"
                    )
                    return

                # Verify amount matches entry fee
                expected_amount = raffle.entry_fee_amount
                if abs(tx["amount"] - expected_amount) > 0.001:  # Allow 0.001 TON tolerance
                    logger.warning(
                        f"Transaction amount mismatch: "
                        f"expected {expected_amount} TON, "
                        f"got {tx['amount']} TON"
                    )
                    # TODO: Implement refund logic for incorrect amounts
                    return

                # Get user
                user = await crud.get_user_by_id(session, user_id)
                if not user:
                    logger.warning(f"User {user_id} not found")
                    return

                # Check if user already participating
                participants = await crud.get_raffle_participants(session, raffle_id)
                if any(p.user_id == user.id for p in participants):
                    logger.warning(
                        f"User {user_id} already participating in raffle {raffle_id}"
                    )
                    # TODO: Implement refund logic for duplicate participation
                    return

                # Check if transaction already processed
                existing_tx = await session.execute(
                    crud.select(crud.Transaction).where(
                        crud.Transaction.transaction_hash == tx["hash"]
                    )
                )
                if existing_tx.scalar_one_or_none():
                    logger.info(f"Transaction {tx['hash'][:8]}... already processed")
                    return

                # Create transaction record
                transaction = await crud.create_transaction(
                    session,
                    user_id=user.id,
                    type=TransactionType.RAFFLE_ENTRY,
                    amount=tx["amount"],
                    currency=CurrencyType.TON,
                    payment_id=tx["hash"][:32],  # Truncate for DB field
                    transaction_hash=tx["hash"],
                    description=f"Участие в розыгрыше #{raffle_id}",
                    payment_metadata={
                        "raffle_id": raffle_id,
                        "from_address": tx["from_address"],
                        "timestamp": tx["timestamp"].isoformat(),
                        "lt": tx["lt"],
                    }
                )

                # Mark transaction as completed
                await crud.update_transaction_status(
                    session, transaction.id, TransactionStatus.COMPLETED
                )

                # Add participant to raffle
                participant = await crud.add_participant(
                    session,
                    raffle_id=raffle_id,
                    user_id=user.id,
                    transaction_id=transaction.id,
                )

                # Get updated participant count
                participants_count = len(await crud.get_raffle_participants(session, raffle_id))

                # Notify user
                await self.bot.send_message(
                    user.telegram_id,
                    f"✅ <b>Оплата подтверждена!</b>\n\n"
                    f"Вы успешно присоединились к розыгрышу #{raffle_id}\n"
                    f"Ваш номер участника: {participant.participant_number}\n\n"
                    f"Получено: {tx['amount']:.4f} TON\n"
                    f"Участников: {participants_count}/{raffle.min_participants}\n\n"
                    f"Розыгрыш начнется автоматически при достижении минимального количества участников.",
                    parse_mode="HTML"
                )

                logger.info(
                    f"User {user.telegram_id} joined raffle {raffle_id}, "
                    f"participant #{participant.participant_number} "
                    f"(tx: {tx['hash'][:8]}...)"
                )

                # Check if raffle should start
                if participants_count >= raffle.min_participants:
                    logger.info(
                        f"Raffle {raffle_id} reached min participants, executing..."
                    )
                    # Execute raffle in background
                    asyncio.create_task(execute_raffle(self.bot, raffle_id))

        except Exception as e:
            logger.error(
                f"Error processing transaction {tx.get('hash', 'unknown')[:8]}...: {e}",
                exc_info=True
            )


async def start_ton_monitor(bot: Bot) -> TonTransactionMonitor:
    """
    Start TON transaction monitor

    Args:
        bot: Telegram Bot instance

    Returns:
        TonTransactionMonitor instance
    """
    monitor = TonTransactionMonitor(bot)
    await monitor.start()
    return monitor
