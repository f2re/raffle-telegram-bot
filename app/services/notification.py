import asyncio
from typing import List, Optional
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from loguru import logger


class NotificationService:
    """Service for sending mass notifications to users"""

    def __init__(self, bot: Bot, messages_per_second: int = 30):
        """
        Initialize notification service

        Args:
            bot: Aiogram Bot instance
            messages_per_second: Max messages per second (Telegram limit is 30)
        """
        self.bot = bot
        self.messages_per_second = messages_per_second

    async def send_to_user(
        self,
        telegram_id: int,
        text: str,
        parse_mode: Optional[str] = "HTML",
        **kwargs
    ) -> bool:
        """
        Send message to a single user

        Args:
            telegram_id: User's Telegram ID
            text: Message text
            parse_mode: Message parse mode
            **kwargs: Additional arguments for send_message

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            await self.bot.send_message(
                chat_id=telegram_id,
                text=text,
                parse_mode=parse_mode,
                **kwargs
            )
            return True
        except TelegramAPIError as e:
            logger.warning(f"Failed to send message to {telegram_id}: {e}")
            return False

    async def send_to_many(
        self,
        telegram_ids: List[int],
        text: str,
        parse_mode: Optional[str] = "HTML",
        **kwargs
    ) -> dict:
        """
        Send message to multiple users with rate limiting

        Args:
            telegram_ids: List of Telegram IDs
            text: Message text
            parse_mode: Message parse mode
            **kwargs: Additional arguments for send_message

        Returns:
            Dictionary with success and failure counts
        """
        total = len(telegram_ids)
        success_count = 0
        failed_count = 0

        logger.info(f"Sending notifications to {total} users")

        # Split into batches
        batch_size = self.messages_per_second
        batches = [
            telegram_ids[i:i + batch_size]
            for i in range(0, len(telegram_ids), batch_size)
        ]

        for batch_num, batch in enumerate(batches, 1):
            logger.debug(f"Processing batch {batch_num}/{len(batches)}")

            # Send all messages in batch concurrently
            tasks = [
                self.send_to_user(telegram_id, text, parse_mode, **kwargs)
                for telegram_id in batch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Count successes
            for result in results:
                if result is True:
                    success_count += 1
                else:
                    failed_count += 1

            # Wait before next batch (except for the last batch)
            if batch_num < len(batches):
                await asyncio.sleep(1)

        logger.info(
            f"Notification complete: {success_count} sent, {failed_count} failed"
        )

        return {
            "total": total,
            "success": success_count,
            "failed": failed_count,
        }

    async def notify_raffle_participants(
        self,
        participant_ids: List[int],
        message: str,
        winner_id: Optional[int] = None,
    ) -> dict:
        """
        Notify raffle participants with priority for winner

        Args:
            participant_ids: List of participant Telegram IDs
            message: Message to send
            winner_id: Winner's Telegram ID (gets priority)

        Returns:
            Dictionary with notification statistics
        """
        # Send to winner first if specified
        if winner_id and winner_id in participant_ids:
            await self.send_to_user(winner_id, message)
            # Remove winner from the list
            participant_ids = [pid for pid in participant_ids if pid != winner_id]
            await asyncio.sleep(0.5)  # Small delay before sending to others

        # Send to all other participants
        return await self.send_to_many(participant_ids, message)
