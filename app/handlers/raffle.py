from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from loguru import logger

from app.database.session import get_session
from app.database import crud
from app.database.models import RaffleStatus, CurrencyType, TransactionType, TransactionStatus
from app.config import settings
from app.keyboards.inline import payment_choice, raffle_info_keyboard, verification_link_keyboard, back_button
from app.services.random_service import random_service, RandomOrgError
from app.services.notification import NotificationService

router = Router()


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
            reply_markup=payment_choice(settings.STARS_ENTRY_FEE, settings.RUB_ENTRY_FEE),
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
        currency_name = "stars" if raffle.entry_fee_type == CurrencyType.STARS else "RUB"

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
            raffle_text += f"🏆 Победитель: {winner.first_name} (@{winner.username})"

        await callback.message.edit_text(
            raffle_text,
            reply_markup=raffle_info_keyboard(raffle.id),
            parse_mode="HTML"
        )

    await callback.answer()


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

        for p in participants[:20]:  # Limit to first 20
            user_display = p.user.first_name
            if p.user.username:
                user_display += f" (@{p.user.username})"
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
                currency_name = "stars" if raffle.entry_fee_type == CurrencyType.STARS else "RUB"
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

            # Set winner
            await crud.set_raffle_winner(
                session,
                raffle_id=raffle_id,
                winner_id=winner_participant.user_id,
                random_result=random_result["full_response"],
                prize_amount=prize_amount,
            )

            # Update winner's balance
            await crud.update_user_balance(
                session,
                user_id=winner_participant.user_id,
                amount=prize_amount,
                currency=raffle.entry_fee_type,
            )

            # Create win transaction
            win_transaction = await crud.create_transaction(
                session,
                user_id=winner_participant.user_id,
                type=TransactionType.RAFFLE_WIN,
                amount=prize_amount,
                currency=raffle.entry_fee_type,
                description=f"Выигрыш в розыгрыше #{raffle_id}",
                payment_metadata={"raffle_id": raffle_id}
            )

            # Mark transaction as completed
            await crud.update_transaction_status(
                session, win_transaction.id, TransactionStatus.COMPLETED
            )

            await session.commit()

            # Get verification URL
            verification_url = random_service.get_verification_url(
                random_result["serial_number"]
            )

            # Send notifications
            notification_service = NotificationService(bot)

            # Winner message
            currency_name = "stars" if raffle.entry_fee_type == CurrencyType.STARS else "RUB"
            prize_str = f"{int(prize_amount)}" if raffle.entry_fee_type == CurrencyType.STARS else f"{prize_amount:.2f}"

            winner_message = (
                f"🎉🎉🎉 <b>ПОЗДРАВЛЯЕМ!</b> 🎉🎉🎉\n\n"
                f"Вы выиграли в розыгрыше #{raffle_id}!\n\n"
                f"💰 Ваш приз: {prize_str} {currency_name}\n"
                f"Средства зачислены на ваш баланс!\n\n"
                f"Участников было: {len(participants)}\n"
                f"Ваш номер: {winner_participant.participant_number}\n"
                f"Выигрышное число: {random_result['random_number']}\n\n"
                f"✨ Розыгрыш проведен честно через Random.org\n"
                f"🔍 Серийный номер для проверки: <code>{random_result['serial_number']}</code>\n"
                f"Нажмите кнопку ниже для проверки честности розыгрыша"
            )

            await notification_service.send_to_user(
                winner_participant.user.telegram_id,
                winner_message,
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
