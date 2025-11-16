from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from loguru import logger

from app.database.session import get_session
from app.database import crud
from app.database.models import RaffleStatus, CurrencyType, TransactionType, TransactionStatus
from app.config import settings
from app.keyboards.inline import payment_choice, raffle_info_keyboard, verification_link_keyboard, back_button
from app.services.random_service import random_service, RandomOrgError
from app.services.notification import NotificationService
from app.services.ton_service import ton_service, TonPaymentError
from app.utils import format_user_display_name, round_rub_amount

router = Router()


@router.message(Command("raffle"))
async def cmd_raffle(message: Message):
    """Handle /raffle command - show current raffle"""
    async with get_session() as session:
        raffle = await crud.get_active_raffle(session)

        if not raffle:
            await message.answer(
                "🎁 <b>Розыгрыш</b>\n\n"
                "Сейчас нет активного розыгрыша.\n"
                "Следующий розыгрыш начнется скоро!",
                reply_markup=back_button(),
                parse_mode="HTML"
            )
            return

        participants = await crud.get_raffle_participants(session, raffle.id)
        participants_count = len(participants)

        # Calculate prize pool with accurate arithmetic
        total_collected = raffle.entry_fee_amount * participants_count

        # For stars, use integer arithmetic; for RUB, use proper rounding
        if raffle.entry_fee_type == CurrencyType.STARS:
            commission = int(total_collected * raffle.commission_percent / 100)
            prize_pool = int(total_collected) - commission
        elif raffle.entry_fee_type == CurrencyType.TON:
            commission = round(total_collected * (raffle.commission_percent / 100), 4)
            prize_pool = round(total_collected - commission, 4)
        else:
            commission = round(total_collected * (raffle.commission_percent / 100), 2)
            prize_pool = round(total_collected - commission, 2)

        currency_symbol = "⭐" if raffle.entry_fee_type == CurrencyType.STARS else ("💎" if raffle.entry_fee_type == CurrencyType.TON else "💳")
        currency_name = "⭐" if raffle.entry_fee_type == CurrencyType.STARS else ("TON" if raffle.entry_fee_type == CurrencyType.TON else "RUB")

        # Format amounts based on currency type
        if raffle.entry_fee_type == CurrencyType.STARS:
            entry_fee_str = f"{int(raffle.entry_fee_amount)}"
            total_str = f"{int(total_collected)}"
            commission_str = f"{int(commission)}"
            prize_str = f"{int(prize_pool)}"
        elif raffle.entry_fee_type == CurrencyType.TON:
            entry_fee_str = f"{raffle.entry_fee_amount:.4f}"
            total_str = f"{total_collected:.4f}"
            commission_str = f"{commission:.4f}"
            prize_str = f"{prize_pool:.4f}"
        else:
            entry_fee_str = f"{raffle.entry_fee_amount:.2f}"
            total_str = f"{total_collected:.2f}"
            commission_str = f"{commission:.2f}"
            prize_str = f"{prize_pool:.2f}"

        raffle_text = (
            f"🎁 <b>Текущий розыгрыш #{raffle.id}</b>\n\n"
            f"Статус: {get_status_emoji(raffle.status)} {raffle.status.value}\n"
            f"Взнос: {currency_symbol} {entry_fee_str} {currency_name}\n"
            f"Участников: {participants_count}/{raffle.min_participants}\n\n"
            f"💰 <b>Призовой фонд:</b>\n"
            f"Собрано: {total_str} {currency_name}\n"
            f"Комиссия ({int(raffle.commission_percent)}%): {commission_str} {currency_name}\n"
            f"<b>Приз победителю: {prize_str} {currency_name}</b>\n\n"
        )

        if raffle.status == RaffleStatus.PENDING:
            raffle_text += f"⏳ Ожидаем еще {raffle.min_participants - participants_count} участников"
        elif raffle.status == RaffleStatus.ACTIVE:
            raffle_text += "🔥 Розыгрыш активен! Скоро определим победителя!"
        elif raffle.status == RaffleStatus.FINISHED and raffle.winner_id:
            winner = await session.get(crud.User, raffle.winner_id)
            # Get current user for privacy check
            current_user = await crud.get_user_by_telegram_id(session, message.from_user.id)
            current_user_id = current_user.id if current_user else None
            winner_display = format_user_display_name(winner, current_user_id)
            raffle_text += f"🏆 Победитель: {winner_display}"

        await message.answer(
            raffle_text,
            reply_markup=raffle_info_keyboard(raffle.id),
            parse_mode="HTML"
        )


@router.message(Command("history"))
async def cmd_history(message: Message):
    """Handle /history command - show user participation history"""
    async with get_session() as session:
        user = await crud.get_user_by_telegram_id(session, message.from_user.id)

        if not user:
            await message.answer(
                "📜 <b>История участия</b>\n\n"
                "Вы еще не участвовали в розыгрышах.",
                reply_markup=back_button(),
                parse_mode="HTML"
            )
            return

        participations = await crud.get_user_participations(session, user.id, limit=10)

        if not participations:
            await message.answer(
                "📜 <b>История участия</b>\n\n"
                "Вы еще не участвовали в розыгрышах.",
                reply_markup=back_button(),
                parse_mode="HTML"
            )
            return

        history_text = "📜 <b>История участия</b>\n\n"

        for p in participations:
            raffle = p.raffle
            status_emoji = get_status_emoji(raffle.status)

            history_text += f"{status_emoji} Розыгрыш #{raffle.id}\n"

            if raffle.winner_id == user.id:
                # Format prize based on currency type
                if raffle.entry_fee_type == CurrencyType.STARS:
                    prize_str = f"{int(raffle.prize_amount)}"
                elif raffle.entry_fee_type == CurrencyType.TON:
                    prize_str = f"{raffle.prize_amount:.4f}"
                else:
                    prize_str = f"{raffle.prize_amount:.2f}"
                currency_name = "⭐" if raffle.entry_fee_type == CurrencyType.STARS else ("TON" if raffle.entry_fee_type == CurrencyType.TON else "RUB")
                history_text += f"🏆 <b>Вы выиграли!</b> Приз: {prize_str} {currency_name}\n"
            elif raffle.status == RaffleStatus.FINISHED:
                history_text += "Не выиграли\n"

            history_text += "\n"

        await message.answer(
            history_text,
            reply_markup=back_button(),
            parse_mode="HTML"
        )


@router.callback_query(F.data == "join_raffle")
async def callback_join_raffle(callback: CallbackQuery):
    """Handle join raffle button"""
    async with get_session() as session:
        raffle = await crud.get_active_raffle(session)

        if not raffle:
            await callback.answer(
                "Сейчас нет активного розыгрыша. Ожидайте следующего!",
                show_alert=True
            )
            return

        # Check if user already participating
        user = await crud.get_user_by_telegram_id(session, callback.from_user.id)
        if user:
            participants = await crud.get_raffle_participants(session, raffle.id)
            if any(p.user_id == user.id for p in participants):
                await callback.answer(
                    "Вы уже участвуете в этом розыгрыше!",
                    show_alert=True
                )
                return

        # Show payment options
        await callback.message.edit_text(
            f"<b>💫 Присоединиться к розыгрышу</b>\n\n"
            f"Выберите способ оплаты:",
            reply_markup=payment_choice(
                stars_fee=settings.STARS_ENTRY_FEE,
                rub_fee=settings.RUB_ENTRY_FEE,
                ton_fee=settings.TON_ENTRY_FEE
            ),
            parse_mode="HTML"
        )

    await callback.answer()


@router.callback_query(F.data.startswith("join_raffle_"))
async def callback_join_raffle_with_id(callback: CallbackQuery):
    """Handle join raffle button with specific raffle ID"""
    raffle_id = int(callback.data.split("_")[2])

    async with get_session() as session:
        raffle = await crud.get_raffle_by_id(session, raffle_id)

        if not raffle:
            await callback.answer(
                "Розыгрыш не найден!",
                show_alert=True
            )
            return

        if raffle.status != RaffleStatus.PENDING:
            await callback.answer(
                "Этот розыгрыш уже завершен или отменен!",
                show_alert=True
            )
            return

        # Check if user already participating
        user = await crud.get_user_by_telegram_id(session, callback.from_user.id)
        if user:
            participants = await crud.get_raffle_participants(session, raffle.id)
            if any(p.user_id == user.id for p in participants):
                await callback.answer(
                    "Вы уже участвуете в этом розыгрыше!",
                    show_alert=True
                )
                return

        # Show payment options
        await callback.message.edit_text(
            f"<b>💫 Присоединиться к розыгрышу</b>\n\n"
            f"Выберите способ оплаты:",
            reply_markup=payment_choice(
                stars_fee=settings.STARS_ENTRY_FEE,
                rub_fee=settings.RUB_ENTRY_FEE,
                ton_fee=settings.TON_ENTRY_FEE
            ),
            parse_mode="HTML"
        )

    await callback.answer()


@router.callback_query(F.data == "current_raffle")
async def callback_current_raffle(callback: CallbackQuery):
    """Show current raffle information"""
    async with get_session() as session:
        raffle = await crud.get_active_raffle(session)

        if not raffle:
            await callback.message.edit_text(
                "🎁 <b>Розыгрыш</b>\n\n"
                "Сейчас нет активного розыгрыша.\n"
                "Следующий розыгрыш начнется скоро!",
                reply_markup=back_button(),
                parse_mode="HTML"
            )
            await callback.answer()
            return

        participants = await crud.get_raffle_participants(session, raffle.id)
        participants_count = len(participants)

        # Calculate prize pool with accurate arithmetic
        total_collected = raffle.entry_fee_amount * participants_count

        # For stars, use integer arithmetic; for RUB, use proper rounding
        if raffle.entry_fee_type == CurrencyType.STARS:
            commission = int(total_collected * raffle.commission_percent / 100)
            prize_pool = int(total_collected) - commission
        else:
            commission = round(total_collected * (raffle.commission_percent / 100), 2)
            prize_pool = round(total_collected - commission, 2)

        currency_symbol = "⭐" if raffle.entry_fee_type == CurrencyType.STARS else "💳"
        currency_name = "⭐" if raffle.entry_fee_type == CurrencyType.STARS else "RUB"

        # Format amounts based on currency type
        if raffle.entry_fee_type == CurrencyType.STARS:
            entry_fee_str = f"{int(raffle.entry_fee_amount)}"
            total_str = f"{int(total_collected)}"
            commission_str = f"{int(commission)}"
            prize_str = f"{int(prize_pool)}"
        else:
            entry_fee_str = f"{raffle.entry_fee_amount:.2f}"
            total_str = f"{total_collected:.2f}"
            commission_str = f"{commission:.2f}"
            prize_str = f"{prize_pool:.2f}"

        raffle_text = (
            f"🎁 <b>Текущий розыгрыш #{raffle.id}</b>\n\n"
            f"Статус: {get_status_emoji(raffle.status)} {raffle.status.value}\n"
            f"Взнос: {currency_symbol} {entry_fee_str} {currency_name}\n"
            f"Участников: {participants_count}/{raffle.min_participants}\n\n"
            f"💰 <b>Призовой фонд:</b>\n"
            f"Собрано: {total_str} {currency_name}\n"
            f"Комиссия ({int(raffle.commission_percent)}%): {commission_str} {currency_name}\n"
            f"<b>Приз победителю: {prize_str} {currency_name}</b>\n\n"
        )

        if raffle.status == RaffleStatus.PENDING:
            raffle_text += f"⏳ Ожидаем еще {raffle.min_participants - participants_count} участников"
        elif raffle.status == RaffleStatus.ACTIVE:
            raffle_text += "🔥 Розыгрыш активен! Скоро определим победителя!"
        elif raffle.status == RaffleStatus.FINISHED and raffle.winner_id:
            winner = await session.get(crud.User, raffle.winner_id)
            # Get current user for privacy check
            current_user = await crud.get_user_by_telegram_id(session, callback.from_user.id)
            current_user_id = current_user.id if current_user else None
            winner_display = format_user_display_name(winner, current_user_id)
            raffle_text += f"🏆 Победитель: {winner_display}"

        await callback.message.edit_text(
            raffle_text,
            reply_markup=raffle_info_keyboard(raffle.id),
            parse_mode="HTML"
        )

    await callback.answer()


@router.callback_query(F.data.startswith("raffle_refresh_"))
async def callback_raffle_refresh(callback: CallbackQuery):
    """Refresh raffle information"""
    raffle_id = int(callback.data.split("_")[2])

    async with get_session() as session:
        raffle = await crud.get_raffle_by_id(session, raffle_id)

        if not raffle:
            await callback.answer("Розыгрыш не найден!", show_alert=True)
            return

        participants = await crud.get_raffle_participants(session, raffle.id)
        participants_count = len(participants)

        # Calculate prize pool with accurate arithmetic
        total_collected = raffle.entry_fee_amount * participants_count

        # For stars, use integer arithmetic; for RUB, use proper rounding
        if raffle.entry_fee_type == CurrencyType.STARS:
            commission = int(total_collected * raffle.commission_percent / 100)
            prize_pool = int(total_collected) - commission
        else:
            commission = round(total_collected * (raffle.commission_percent / 100), 2)
            prize_pool = round(total_collected - commission, 2)

        currency_symbol = "⭐" if raffle.entry_fee_type == CurrencyType.STARS else "💳"
        currency_name = "⭐" if raffle.entry_fee_type == CurrencyType.STARS else "RUB"

        # Format amounts based on currency type
        if raffle.entry_fee_type == CurrencyType.STARS:
            entry_fee_str = f"{int(raffle.entry_fee_amount)}"
            total_str = f"{int(total_collected)}"
            commission_str = f"{int(commission)}"
            prize_str = f"{int(prize_pool)}"
        else:
            entry_fee_str = f"{raffle.entry_fee_amount:.2f}"
            total_str = f"{total_collected:.2f}"
            commission_str = f"{commission:.2f}"
            prize_str = f"{prize_pool:.2f}"

        raffle_text = (
            f"🎁 <b>Текущий розыгрыш #{raffle.id}</b>\n\n"
            f"Статус: {get_status_emoji(raffle.status)} {raffle.status.value}\n"
            f"Взнос: {currency_symbol} {entry_fee_str} {currency_name}\n"
            f"Участников: {participants_count}/{raffle.min_participants}\n\n"
            f"💰 <b>Призовой фонд:</b>\n"
            f"Собрано: {total_str} {currency_name}\n"
            f"Комиссия ({int(raffle.commission_percent)}%): {commission_str} {currency_name}\n"
            f"<b>Приз победителю: {prize_str} {currency_name}</b>\n\n"
        )

        if raffle.status == RaffleStatus.PENDING:
            raffle_text += f"⏳ Ожидаем еще {raffle.min_participants - participants_count} участников"
        elif raffle.status == RaffleStatus.ACTIVE:
            raffle_text += "🔥 Розыгрыш активен! Скоро определим победителя!"
        elif raffle.status == RaffleStatus.FINISHED and raffle.winner_id:
            winner = await session.get(crud.User, raffle.winner_id)
            # Get current user for privacy check
            current_user = await crud.get_user_by_telegram_id(session, callback.from_user.id)
            current_user_id = current_user.id if current_user else None
            winner_display = format_user_display_name(winner, current_user_id)
            raffle_text += f"🏆 Победитель: {winner_display}"

        await callback.message.edit_text(
            raffle_text,
            reply_markup=raffle_info_keyboard(raffle.id),
            parse_mode="HTML"
        )

    await callback.answer("Обновлено! ✅")


@router.callback_query(F.data.startswith("raffle_participants_"))
async def callback_raffle_participants(callback: CallbackQuery):
    """Show raffle participants list"""
    raffle_id = int(callback.data.split("_")[2])

    async with get_session() as session:
        participants = await crud.get_raffle_participants(session, raffle_id)

        if not participants:
            await callback.answer("Пока нет участников")
            return

        participants_text = f"<b>👥 Участники розыгрыша #{raffle_id}</b>\n\n"

        # Get current user for privacy check
        current_user = await crud.get_user_by_telegram_id(session, callback.from_user.id)
        current_user_id = current_user.id if current_user else None

        for p in participants[:20]:  # Limit to first 20
            user_display = format_user_display_name(p.user, current_user_id)
            participants_text += f"{p.participant_number}. {user_display}\n"

        if len(participants) > 20:
            participants_text += f"\n... и еще {len(participants) - 20} участников"

        await callback.message.edit_text(
            participants_text,
            reply_markup=raffle_info_keyboard(raffle_id),
            parse_mode="HTML"
        )

    await callback.answer()


@router.callback_query(F.data == "history")
async def callback_history(callback: CallbackQuery):
    """Show user participation history"""
    async with get_session() as session:
        user = await crud.get_user_by_telegram_id(session, callback.from_user.id)

        if not user:
            await callback.answer("Вы еще не участвовали в розыгрышах")
            return

        participations = await crud.get_user_participations(session, user.id, limit=10)

        if not participations:
            await callback.message.edit_text(
                "📜 <b>История участия</b>\n\n"
                "Вы еще не участвовали в розыгрышах.",
                reply_markup=back_button(),
                parse_mode="HTML"
            )
            await callback.answer()
            return

        history_text = "📜 <b>История участия</b>\n\n"

        for p in participations:
            raffle = p.raffle
            status_emoji = get_status_emoji(raffle.status)

            history_text += f"{status_emoji} Розыгрыш #{raffle.id}\n"

            if raffle.winner_id == user.id:
                # Format prize based on currency type
                if raffle.entry_fee_type == CurrencyType.STARS:
                    prize_str = f"{int(raffle.prize_amount)}"
                else:
                    prize_str = f"{raffle.prize_amount:.2f}"
                currency_name = "⭐" if raffle.entry_fee_type == CurrencyType.STARS else "RUB"
                history_text += f"🏆 <b>Вы выиграли!</b> Приз: {prize_str} {currency_name}\n"
            elif raffle.status == RaffleStatus.FINISHED:
                history_text += "Не выиграли\n"

            history_text += "\n"

        await callback.message.edit_text(
            history_text,
            reply_markup=back_button(),
            parse_mode="HTML"
        )

    await callback.answer()


def get_status_emoji(status: RaffleStatus) -> str:
    """Get emoji for raffle status"""
    emoji_map = {
        RaffleStatus.PENDING: "⏳",
        RaffleStatus.ACTIVE: "🔥",
        RaffleStatus.FINISHED: "✅",
        RaffleStatus.CANCELLED: "❌",
    }
    return emoji_map.get(status, "❓")


async def handle_ton_payout(bot: Bot, session, raffle_id: int, winner, prize_amount: float):
    """
    Handle automatic TON payout to winner

    Args:
        bot: Bot instance
        session: Database session
        raffle_id: Raffle ID
        winner: Winner user object
        prize_amount: Prize amount in TON
    """
    try:
        # Check if winner has TON wallet address
        if not winner.ton_wallet_address:
            # Winner hasn't set wallet - notify them and ask to set it
            await bot.send_message(
                winner.telegram_id,
                f"🎉 <b>Поздравляем! Вы победили в розыгрыше #{raffle_id}!</b>\n\n"
                f"Ваш приз: <b>{prize_amount:.4f} TON</b>\n\n"
                f"⚠️ Для получения приза необходимо указать адрес TON кошелька.\n\n"
                f"Используйте команду /balance и укажите ваш TON кошелек.\n"
                f"После этого приз будет отправлен автоматически.",
                parse_mode="HTML"
            )

            logger.warning(
                f"Winner {winner.telegram_id} for raffle {raffle_id} "
                f"doesn't have TON wallet address set"
            )
            return

        # Send TON to winner
        logger.info(
            f"Sending {prize_amount:.4f} TON to winner {winner.telegram_id} "
            f"(wallet: {winner.ton_wallet_address[:8]}...)"
        )

        tx_hash = await ton_service.send_prize_payout(
            winner_address=winner.ton_wallet_address,
            amount_ton=prize_amount,
            raffle_id=raffle_id
        )

        # Create transaction record
        await crud.create_transaction(
            session,
            user_id=winner.id,
            type=TransactionType.RAFFLE_WIN,
            amount=prize_amount,
            currency=CurrencyType.TON,
            payment_id=tx_hash[:32],  # Truncate for DB
            transaction_hash=tx_hash,
            description=f"Приз за победу в розыгрыше #{raffle_id}",
            payment_metadata={
                "raffle_id": raffle_id,
                "winner_wallet": winner.ton_wallet_address,
                "automatic_payout": True
            }
        )

        await session.commit()

        # Notify winner
        await bot.send_message(
            winner.telegram_id,
            f"🎉 <b>Поздравляем с победой!</b>\n\n"
            f"💎 Приз <b>{prize_amount:.4f} TON</b> отправлен на ваш кошелек!\n"
            f"🏆 Розыгрыш: #{raffle_id}\n\n"
            f"📝 Адрес получателя: <code>{winner.ton_wallet_address}</code>\n"
            f"🔗 Хэш транзакции: <code>{tx_hash[:16]}...</code>\n\n"
            f"Приз поступит на ваш кошелек в течение нескольких секунд.\n"
            f"Проверьте баланс в Tonkeeper или вашем TON кошельке!",
            parse_mode="HTML"
        )

        logger.info(
            f"TON payout sent successfully: raffle={raffle_id}, "
            f"winner={winner.telegram_id}, amount={prize_amount}, "
            f"tx_hash={tx_hash[:16]}..."
        )

    except TonPaymentError as e:
        logger.error(f"Failed to send TON payout: {e}")

        # Notify winner about the issue
        await bot.send_message(
            winner.telegram_id,
            f"🎉 <b>Поздравляем с победой!</b>\n\n"
            f"Ваш приз: <b>{prize_amount:.4f} TON</b>\n\n"
            f"⚠️ К сожалению, возникла техническая ошибка при автоматической отправке приза.\n"
            f"Администратор свяжется с вами для ручной выплаты.\n\n"
            f"Приносим извинения за неудобства!",
            parse_mode="HTML"
        )

        # Notify admin
        admin_ids = settings.get_admin_ids()
        if admin_ids:
            await bot.send_message(
                admin_ids[0],
                f"⚠️ <b>Ошибка автоматической выплаты TON</b>\n\n"
                f"Розыгрыш: #{raffle_id}\n"
                f"Победитель: {winner.first_name} (@{winner.username or 'без username'})\n"
                f"Telegram ID: {winner.telegram_id}\n"
                f"Сумма: {prize_amount:.4f} TON\n"
                f"Кошелек: <code>{winner.ton_wallet_address}</code>\n\n"
                f"Ошибка: {str(e)}\n\n"
                f"Необходимо выплатить приз вручную!",
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Unexpected error in TON payout: {e}", exc_info=True)
        # Same error handling as above
        await bot.send_message(
            winner.telegram_id,
            f"🎉 Поздравляем с победой! Приз {prize_amount:.4f} TON\n"
            f"⚠️ Возникла техническая ошибка. Администратор свяжется с вами.",
            parse_mode="HTML"
        )


async def execute_raffle(bot: Bot, raffle_id: int):
    """
    Execute raffle and determine winner

    This function should be called when minimum participants is reached
    """
    async with get_session() as session:
        raffle = await crud.get_raffle_by_id(session, raffle_id)

        if not raffle or raffle.status != RaffleStatus.PENDING:
            logger.warning(f"Cannot execute raffle {raffle_id}: invalid status")
            return

        participants = await crud.get_raffle_participants(session, raffle_id)

        if len(participants) < raffle.min_participants:
            logger.warning(
                f"Cannot execute raffle {raffle_id}: "
                f"not enough participants ({len(participants)}/{raffle.min_participants})"
            )
            return

        logger.info(f"Executing raffle {raffle_id} with {len(participants)} participants")

        # Update status to ACTIVE
        await crud.update_raffle_status(session, raffle_id, RaffleStatus.ACTIVE)

        try:
            # Get random number from Random.org
            random_result = random_service.get_signed_random(1, len(participants))
            winner_index = random_result["random_number"] - 1  # Convert to 0-based index
            winner_participant = participants[winner_index]

            # Calculate prize with accurate arithmetic
            total_collected = raffle.entry_fee_amount * len(participants)

            # For stars, use integer arithmetic; for RUB, use proper rounding
            if raffle.entry_fee_type == CurrencyType.STARS:
                commission = int(total_collected * raffle.commission_percent / 100)
                prize_amount = int(total_collected) - commission
            else:
                commission = round(total_collected * (raffle.commission_percent / 100), 2)
                prize_amount = round(total_collected - commission, 2)

            # Round to whole rubles if currency is RUB
            if raffle.entry_fee_type == CurrencyType.RUB:
                prize_amount = round_rub_amount(prize_amount)

            # Set winner
            await crud.set_raffle_winner(
                session,
                raffle_id=raffle_id,
                winner_id=winner_participant.user_id,
                random_result=random_result["full_response"],
                prize_amount=prize_amount,
            )

            await session.commit()

            # Handle payouts based on currency type
            if raffle.entry_fee_type == CurrencyType.TON:
                # TON: Automatic payout directly to winner's wallet
                await handle_ton_payout(
                    bot=bot,
                    session=session,
                    raffle_id=raffle_id,
                    winner=winner_participant.user,
                    prize_amount=prize_amount
                )
            else:
                # STARS/RUB: Send payout request to admin (legacy system)
                # This allows admin to pay winner via invoice link
                from app.services.admin_payout_service import create_admin_payout_service

                payout_service = create_admin_payout_service(bot)

                # Get first admin ID from settings
                admin_ids = settings.get_admin_ids()
                if not admin_ids:
                    logger.error("No admin IDs configured for payout request!")
                    raise ValueError("No admin IDs configured")

                admin_id = admin_ids[0]  # Send to first admin

                # Notify winner that payout is pending
                await payout_service.notify_winner_payment_pending(
                    winner_id=winner_participant.user.telegram_id,
                    amount=prize_amount,
                    raffle_id=raffle_id,
                    currency=raffle.entry_fee_type,
                )

                # Send payout request to admin
                await payout_service.send_payout_request_to_admin(
                    admin_id=admin_id,
                    winner_id=winner_participant.user.telegram_id,
                    winner_username=winner_participant.user.username,
                    winner_name=winner_participant.user.first_name or "Пользователь",
                    amount=prize_amount,
                    raffle_id=raffle_id,
                    currency=raffle.entry_fee_type,
                )

                logger.info(
                    f"Payout request sent to admin {admin_id} for raffle {raffle_id}"
                )

            # Get verification URL
            verification_url = random_service.get_verification_url(
                random_result["full_response"]
            )

            # Send notifications
            notification_service = NotificationService(bot)

            # Winner message - updated to reflect admin payout system
            currency_name = "⭐" if raffle.entry_fee_type == CurrencyType.STARS else "RUB"
            currency_symbol = "⭐" if raffle.entry_fee_type == CurrencyType.STARS else "₽"
            prize_str = f"{int(prize_amount)}" if raffle.entry_fee_type == CurrencyType.STARS else f"{prize_amount:.2f}"

            # Note: Winner already received notification from payout_service.notify_winner_payment_pending
            # This is the notification for all participants about the raffle results

            # Send verification link to winner separately
            winner_verification_message = (
                f"✨ <b>Проверка честности розыгрыша</b>\n\n"
                f"Участников было: {len(participants)}\n"
                f"Ваш номер: {winner_participant.participant_number}\n"
                f"Выигрышное число: {random_result['random_number']}\n\n"
                f"Розыгрыш проведен честно через Random.org\n"
                f"🔍 Серийный номер: <code>{random_result['serial_number']}</code>\n"
                f"Нажмите кнопку ниже для проверки честности розыгрыша"
            )

            await notification_service.send_to_user(
                winner_participant.user.telegram_id,
                winner_verification_message,
                reply_markup=verification_link_keyboard(verification_url)
            )

            # Participants message
            participant_ids = [
                p.user.telegram_id for p in participants
                if p.user_id != winner_participant.user_id
            ]

            participants_message = (
                f"🎁 <b>Розыгрыш #{raffle_id} завершен!</b>\n\n"
                f"Победитель: {winner_participant.user.first_name}\n"
                f"Номер победителя: {winner_participant.participant_number}\n"
                f"Выигрышное число: {random_result['random_number']}\n\n"
                f"Всего участников: {len(participants)}\n"
                f"Приз: {prize_str} {currency_name}\n\n"
                f"✨ Результат проверяемый через Random.org\n"
                f"🔍 Серийный номер для проверки: <code>{random_result['serial_number']}</code>\n"
                f"Проверьте честность розыгрыша по ссылке ниже!\n\n"
                f"Удачи в следующий раз! 🍀"
            )

            await notification_service.send_to_many(
                participant_ids,
                participants_message,
                reply_markup=verification_link_keyboard(verification_url)
            )

            logger.info(
                f"Raffle {raffle_id} completed. "
                f"Winner: user_id={winner_participant.user_id}, "
                f"prize={prize_amount}"
            )

        except RandomOrgError as e:
            logger.error(f"Random.org error during raffle {raffle_id}: {e}")
            # Rollback raffle status
            await crud.update_raffle_status(session, raffle_id, RaffleStatus.PENDING)
            await session.commit()

        except Exception as e:
            logger.error(f"Error executing raffle {raffle_id}: {e}", exc_info=True)
            await crud.update_raffle_status(session, raffle_id, RaffleStatus.PENDING)
            await session.commit()
