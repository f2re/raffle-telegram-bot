from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

from app.database.session import get_session
from app.database import crud
from app.database.models import CurrencyType, RaffleStatus, WithdrawalStatus, Transaction, TransactionStatus, PayoutStatus
from app.config import settings
from app.keyboards.inline import admin_menu, confirm_raffle_start, back_button, admin_withdrawal_keyboard
from app.handlers.raffle import execute_raffle
from app.utils import format_currency_amount, format_user_display_name
from app.services.payment_service import yookassa_service, PaymentError

router = Router()


class AdminStates(StatesGroup):
    """States for admin operations"""
    waiting_for_min_participants = State()
    waiting_for_entry_fee = State()
    waiting_for_commission = State()


def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return settings.is_admin(user_id)


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Handle /admin command"""
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет доступа к админ-панели.")
        return

    await message.answer(
        "<b>🔧 Админ-панель</b>\n\n"
        "Выберите действие:",
        reply_markup=admin_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_menu")
async def callback_admin_menu(callback: CallbackQuery):
    """Show admin menu"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    await callback.message.edit_text(
        "<b>🔧 Админ-панель</b>\n\n"
        "Выберите действие:",
        reply_markup=admin_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_create_raffle")
async def callback_admin_create_raffle(callback: CallbackQuery, state: FSMContext):
    """Start raffle creation process"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    # Check if there's already an active raffle
    async with get_session() as session:
        active_raffle = await crud.get_active_raffle(session)
        if active_raffle:
            await callback.answer(
                "Уже есть активный розыгрыш! Завершите его перед созданием нового.",
                show_alert=True
            )
            return

    await callback.message.edit_text(
        "<b>📝 Создание нового розыгрыша</b>\n\n"
        "Введите минимальное количество участников:",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_min_participants)
    await callback.answer()


@router.message(AdminStates.waiting_for_min_participants)
async def process_min_participants(message: Message, state: FSMContext):
    """Process minimum participants input"""
    if not is_admin(message.from_user.id):
        return

    try:
        min_participants = int(message.text)
        if min_participants < 2:
            await message.answer("Минимум должно быть хотя бы 2 участника!")
            return

        await state.update_data(min_participants=min_participants)

        await message.answer(
            f"✅ Минимум участников: {min_participants}\n\n"
            "Теперь выберите тип валюты для взноса:\n"
            "Отправьте 'stars' для звезд или 'rub' для рублей",
        )
        await state.set_state(AdminStates.waiting_for_entry_fee)

    except ValueError:
        await message.answer("Пожалуйста, введите число!")


@router.message(AdminStates.waiting_for_entry_fee)
async def process_entry_fee(message: Message, state: FSMContext):
    """Process entry fee type"""
    if not is_admin(message.from_user.id):
        return

    currency_text = message.text.lower().strip()

    if currency_text == "stars":
        currency_type = CurrencyType.STARS
        entry_fee = settings.STARS_ENTRY_FEE
        commission = settings.STARS_COMMISSION_PERCENT
    elif currency_text == "rub":
        currency_type = CurrencyType.RUB
        entry_fee = settings.RUB_ENTRY_FEE
        commission = settings.RUB_COMMISSION_PERCENT
    else:
        await message.answer("Введите 'stars' или 'rub'")
        return

    await state.update_data(
        currency_type=currency_type,
        entry_fee=entry_fee,
        commission=commission
    )

    # Create raffle
    data = await state.get_data()

    async with get_session() as session:
        raffle = await crud.create_raffle(
            session,
            min_participants=data["min_participants"],
            entry_fee_type=currency_type,
            entry_fee_amount=entry_fee,
            commission_percent=commission,
        )

        currency_name = "stars" if currency_type == CurrencyType.STARS else "RUB"

        await message.answer(
            f"✅ <b>Розыгрыш создан!</b>\n\n"
            f"ID: #{raffle.id}\n"
            f"Минимум участников: {data['min_participants']}\n"
            f"Взнос: {entry_fee} {currency_name}\n"
            f"Комиссия: {commission}%\n\n"
            f"Розыгрыш активирован и готов к приему участников!",
            reply_markup=admin_menu(),
            parse_mode="HTML"
        )

        logger.info(f"Admin created raffle #{raffle.id}")

    await state.clear()


@router.callback_query(F.data == "admin_current_raffle")
async def callback_admin_current_raffle(callback: CallbackQuery):
    """Show current raffle info for admin"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    async with get_session() as session:
        raffle = await crud.get_active_raffle(session)

        if not raffle:
            await callback.message.edit_text(
                "Нет активного розыгрыша.",
                reply_markup=admin_menu(),
                parse_mode="HTML"
            )
            await callback.answer()
            return

        participants = await crud.get_raffle_participants(session, raffle.id)
        participants_count = len(participants)

        # Calculate with accurate arithmetic
        total_collected = raffle.entry_fee_amount * participants_count

        # For stars, use integer arithmetic; for RUB, use proper rounding
        if raffle.entry_fee_type == CurrencyType.STARS:
            commission = int(total_collected * raffle.commission_percent / 100)
            prize_pool = int(total_collected) - commission
        else:
            commission = round(total_collected * (raffle.commission_percent / 100), 2)
            prize_pool = round(total_collected - commission, 2)

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
            f"<b>📊 Текущий розыгрыш #{raffle.id}</b>\n\n"
            f"Статус: {raffle.status.value}\n"
            f"Участников: {participants_count}/{raffle.min_participants}\n"
            f"Взнос: {entry_fee_str} {currency_name}\n\n"
            f"💰 Собрано: {total_str} {currency_name}\n"
            f"💸 Комиссия: {commission_str} {currency_name}\n"
            f"🏆 Приз: {prize_str} {currency_name}\n"
        )

        await callback.message.edit_text(
            raffle_text,
            reply_markup=admin_menu(),
            parse_mode="HTML"
        )

    await callback.answer()


@router.callback_query(F.data == "admin_start_raffle")
async def callback_admin_start_raffle(callback: CallbackQuery):
    """Force start raffle"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    async with get_session() as session:
        raffle = await crud.get_active_raffle(session)

        if not raffle:
            await callback.answer("Нет активного розыгрыша", show_alert=True)
            return

        if raffle.status != RaffleStatus.PENDING:
            await callback.answer("Розыгрыш уже запущен или завершен", show_alert=True)
            return

        participants = await crud.get_raffle_participants(session, raffle.id)

        if len(participants) < 2:
            await callback.answer(
                "Нужно хотя бы 2 участника для розыгрыша!",
                show_alert=True
            )
            return

        await callback.message.edit_text(
            f"<b>⚠️ Принудительный запуск розыгрыша</b>\n\n"
            f"Розыгрыш #{raffle.id}\n"
            f"Участников: {len(participants)}\n\n"
            f"Подтвердите запуск:",
            reply_markup=confirm_raffle_start(),
            parse_mode="HTML"
        )

    await callback.answer()


@router.callback_query(F.data == "admin_confirm_start")
async def callback_admin_confirm_start(callback: CallbackQuery):
    """Confirm and execute raffle"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    async with get_session() as session:
        raffle = await crud.get_active_raffle(session)

        if not raffle or raffle.status != RaffleStatus.PENDING:
            await callback.answer("Розыгрыш недоступен для запуска", show_alert=True)
            return

    await callback.message.edit_text(
        "⏳ Запускаем розыгрыш...",
        parse_mode="HTML"
    )

    # Execute raffle
    bot = callback.bot
    await execute_raffle(bot, raffle.id)

    await callback.message.edit_text(
        "✅ Розыгрыш завершен! Победитель определен.",
        reply_markup=admin_menu(),
        parse_mode="HTML"
    )

    await callback.answer()


@router.callback_query(F.data == "admin_stop_raffle")
async def callback_admin_stop_raffle(callback: CallbackQuery):
    """Stop/cancel current raffle"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    async with get_session() as session:
        raffle = await crud.get_active_raffle(session)

        if not raffle:
            await callback.answer("Нет активного розыгрыша", show_alert=True)
            return

        await crud.update_raffle_status(session, raffle.id, RaffleStatus.CANCELLED)

        await callback.message.edit_text(
            f"❌ Розыгрыш #{raffle.id} остановлен",
            reply_markup=admin_menu(),
            parse_mode="HTML"
        )

        logger.info(f"Admin cancelled raffle #{raffle.id}")

    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: CallbackQuery):
    """Show bot statistics"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    async with get_session() as session:
        # Get total users
        from sqlalchemy import select, func
        from app.database.models import User, Raffle, Transaction

        users_count = await session.scalar(select(func.count(User.id)))
        raffles_count = await session.scalar(select(func.count(Raffle.id)))
        finished_raffles = await session.scalar(
            select(func.count(Raffle.id)).where(Raffle.status == RaffleStatus.FINISHED)
        )

        stats_text = (
            "<b>📊 Статистика бота</b>\n\n"
            f"👥 Всего пользователей: {users_count}\n"
            f"🎁 Всего розыгрышей: {raffles_count}\n"
            f"✅ Завершено: {finished_raffles}\n"
        )

        await callback.message.edit_text(
            stats_text,
            reply_markup=admin_menu(),
            parse_mode="HTML"
        )

    await callback.answer()


@router.callback_query(F.data == "admin_settings")
async def callback_admin_settings(callback: CallbackQuery):
    """Show bot settings"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    settings_text = (
        "<b>⚙️ Настройки бота</b>\n\n"
        f"⭐ Взнос (Stars): {settings.STARS_ENTRY_FEE}\n"
        f"⭐ Комиссия (Stars): {settings.STARS_COMMISSION_PERCENT}%\n\n"
        f"💳 Взнос (RUB): {settings.RUB_ENTRY_FEE}\n"
        f"💳 Комиссия (RUB): {settings.RUB_COMMISSION_PERCENT}%\n\n"
        f"👥 Минимум участников: {settings.MIN_PARTICIPANTS}\n\n"
        f"🔒 Показывать username: {settings.SHOW_USERNAMES}\n\n"
        f"Для изменения настроек отредактируйте .env файл"
    )

    await callback.message.edit_text(
        settings_text,
        reply_markup=admin_menu(),
        parse_mode="HTML"
    )

    await callback.answer()


@router.callback_query(F.data == "admin_withdrawals")
async def callback_admin_withdrawals(callback: CallbackQuery):
    """Show pending withdrawal requests"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    async with get_session() as session:
        pending_withdrawals = await crud.get_pending_withdrawals(session, limit=10)

        if not pending_withdrawals:
            await callback.message.edit_text(
                "<b>💸 Заявки на вывод</b>\n\n"
                "Нет ожидающих заявок",
                reply_markup=admin_menu(),
                parse_mode="HTML"
            )
            await callback.answer()
            return

        withdrawals_text = "<b>💸 Заявки на вывод (ожидают)</b>\n\n"

        for w in pending_withdrawals[:5]:  # Show first 5
            user_display = format_user_display_name(w.user, show_username=True)

            withdrawals_text += f"ID: #{w.id}\n"
            withdrawals_text += f"Пользователь: {user_display}\n"
            withdrawals_text += f"Сумма: {format_currency_amount(w.amount, w.currency)}\n"

            # Show payment details
            if w.card_number:
                masked_card = f"**** **** **** {w.card_number[-4:]}"
                withdrawals_text += f"💳 Карта: {masked_card}\n"
            elif w.phone_number:
                withdrawals_text += f"📱 Телефон: {w.phone_number}\n"
            else:
                withdrawals_text += "⭐ Telegram Stars\n"

            withdrawals_text += f"Дата: {w.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"

        if len(pending_withdrawals) > 5:
            withdrawals_text += f"... и еще {len(pending_withdrawals) - 5} заявок\n\n"

        withdrawals_text += "Нажмите ID заявки для просмотра деталей"

        # Create keyboard with withdrawal IDs
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton

        builder = InlineKeyboardBuilder()

        for w in pending_withdrawals[:5]:
            builder.row(
                InlineKeyboardButton(
                    text=f"Заявка #{w.id}",
                    callback_data=f"admin_view_withdrawal_{w.id}"
                )
            )

        builder.row(
            InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")
        )

        await callback.message.edit_text(
            withdrawals_text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )

    await callback.answer()


@router.callback_query(F.data.startswith("admin_view_withdrawal_"))
async def callback_admin_view_withdrawal(callback: CallbackQuery):
    """View specific withdrawal request"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    withdrawal_id = int(callback.data.split("_")[-1])

    async with get_session() as session:
        withdrawal = await crud.get_withdrawal_request(session, withdrawal_id)

        if not withdrawal:
            await callback.answer("Заявка не найдена", show_alert=True)
            return

        user_display = format_user_display_name(withdrawal.user, show_username=True)

        withdrawal_text = f"<b>💸 Заявка на вывод #{withdrawal.id}</b>\n\n"
        withdrawal_text += f"Пользователь: {user_display}\n"
        withdrawal_text += f"User ID: {withdrawal.user.telegram_id}\n"
        withdrawal_text += f"Сумма: {format_currency_amount(withdrawal.amount, withdrawal.currency)}\n"
        withdrawal_text += f"Статус: {withdrawal.status.value}\n\n"

        # Show payment details
        if withdrawal.card_number:
            withdrawal_text += f"💳 <b>Карта:</b> {withdrawal.card_number}\n"
        elif withdrawal.phone_number:
            withdrawal_text += f"📱 <b>Телефон:</b> {withdrawal.phone_number}\n"
        else:
            withdrawal_text += "⭐ <b>Telegram Stars</b>\n"

        withdrawal_text += f"\nДата создания: {withdrawal.created_at.strftime('%d.%m.%Y %H:%M')}"

        # Show current balance
        user = withdrawal.user
        if withdrawal.currency == CurrencyType.STARS:
            withdrawal_text += f"\n\nТекущий баланс: {int(user.balance_stars)} ⭐"
        else:
            withdrawal_text += f"\n\nТекущий баланс: {int(user.balance_rub)} ₽"

        await callback.message.edit_text(
            withdrawal_text,
            reply_markup=admin_withdrawal_keyboard(withdrawal.id),
            parse_mode="HTML"
        )

    await callback.answer()


@router.callback_query(F.data.startswith("admin_approve_withdrawal_"))
async def callback_admin_approve_withdrawal(callback: CallbackQuery):
    """Approve withdrawal request"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    withdrawal_id = int(callback.data.split("_")[-1])

    async with get_session() as session:
        withdrawal = await crud.get_withdrawal_request(session, withdrawal_id)

        if not withdrawal:
            await callback.answer("Заявка не найдена", show_alert=True)
            return

        if withdrawal.status != WithdrawalStatus.PENDING:
            await callback.answer("Заявка уже обработана", show_alert=True)
            return

        # Check user balance
        user = withdrawal.user
        balance = user.balance_stars if withdrawal.currency == CurrencyType.STARS else user.balance_rub

        if withdrawal.amount > balance:
            await callback.answer(
                f"Ошибка: недостаточно средств у пользователя!\n"
                f"Запрошено: {withdrawal.amount}, Баланс: {balance}",
                show_alert=True
            )
            return

        # Get admin user for admin_id
        admin_user = await crud.get_user_by_telegram_id(session, callback.from_user.id)

        # Update withdrawal status
        await crud.update_withdrawal_status(
            session,
            withdrawal_id=withdrawal.id,
            status=WithdrawalStatus.APPROVED,
            admin_id=admin_user.id if admin_user else None
        )

        # Deduct from user balance
        deduct_amount = -withdrawal.amount
        await crud.update_user_balance(
            session,
            user_id=user.id,
            amount=deduct_amount,
            currency=withdrawal.currency
        )

        await session.commit()

        # Handle star transfers with improved multi-refund logic
        total_refunded = 0
        remaining_amount = 0
        admin_note = ""

        if withdrawal.currency == CurrencyType.STARS:
            # Get ALL eligible star transactions for refund (within 21 days)
            from app.database.models import TransactionType
            from sqlalchemy import select, desc
            from datetime import datetime, timedelta

            # Find all star payments within refund window (21 days)
            refund_cutoff = datetime.utcnow() - timedelta(days=21)

            star_transactions_result = await session.execute(
                select(Transaction)
                .where(
                    Transaction.user_id == user.id,
                    Transaction.currency == CurrencyType.STARS,
                    Transaction.type == TransactionType.RAFFLE_ENTRY,
                    Transaction.status == TransactionStatus.COMPLETED,
                    Transaction.payment_id.isnot(None),
                    Transaction.created_at >= refund_cutoff
                )
                .order_by(desc(Transaction.created_at))
            )
            star_transactions = star_transactions_result.scalars().all()

            if star_transactions:
                # Try to refund using multiple transactions
                try:
                    from app.services.stars_service import create_stars_service
                    stars_service = create_stars_service(callback.bot)

                    refund_result = await stars_service.process_withdrawal_with_multiple_refunds(
                        user_id=user.id,
                        telegram_id=user.telegram_id,
                        withdrawal_amount=int(withdrawal.amount),
                        transactions=star_transactions
                    )

                    total_refunded = refund_result["total_refunded"]
                    remaining_amount = refund_result["remaining"]
                    successful_count = len(refund_result["successful_refunds"])

                    # Build detailed admin note
                    if total_refunded > 0:
                        admin_note = (
                            f"✅ <b>Автоматический возврат выполнен</b>\n"
                            f"Возвращено: {total_refunded} ⭐ через {successful_count} платеж(ей)\n"
                        )

                    if remaining_amount > 0:
                        if total_refunded > 0:
                            admin_note += f"\n⚠️ <b>Остаток для ручной отправки</b>\n"
                        else:
                            admin_note += f"⚠️ <b>Требуется ручная отправка</b>\n"

                        admin_note += (
                            f"Отправьте {remaining_amount} ⭐ пользователю вручную:\n"
                            f"• User ID: <code>{user.telegram_id}</code>\n"
                        )
                        if user.username:
                            admin_note += f"• Username: @{user.username}\n"

                        admin_note += (
                            f"\n<b>Как отправить:</b>\n"
                            f"1. Используйте другого бота или личный аккаунт\n"
                            f"2. Отправьте подарок на сумму {remaining_amount} ⭐\n"
                            f"3. Или договоритесь с пользователем об альтернативе"
                        )

                    logger.info(
                        f"Star withdrawal processed: "
                        f"user={user.telegram_id}, "
                        f"requested={withdrawal.amount}, "
                        f"refunded={total_refunded}, "
                        f"remaining={remaining_amount}"
                    )

                except Exception as e:
                    logger.error(f"Failed to process star refunds: {e}", exc_info=True)
                    remaining_amount = int(withdrawal.amount)
                    admin_note = (
                        f"❌ <b>Ошибка автоматического возврата</b>\n"
                        f"Отправьте {remaining_amount} ⭐ вручную пользователю\n"
                        f"User ID: <code>{user.telegram_id}</code>\n"
                    )
                    if user.username:
                        admin_note += f"Username: @{user.username}\n"
                    admin_note += f"\nОшибка: {str(e)}"
            else:
                # No eligible transactions for refund
                remaining_amount = int(withdrawal.amount)
                admin_note = (
                    f"⚠️ <b>Нет платежей для автоматического возврата</b>\n"
                    f"У пользователя нет платежей за последние 21 день.\n\n"
                    f"Отправьте {remaining_amount} ⭐ вручную:\n"
                    f"• User ID: <code>{user.telegram_id}</code>\n"
                )
                if user.username:
                    admin_note += f"• Username: @{user.username}\n"

                admin_note += (
                    f"\n<b>Способы отправки:</b>\n"
                    f"1. Через другого бота (как подарок)\n"
                    f"2. С личного аккаунта в Telegram\n"
                    f"3. Предложить пользователю альтернативу (например, рубли)"
                )

        # Notify user
        from app.services.notification import NotificationService
        bot = callback.bot
        notification_service = NotificationService(bot)

        user_message = (
            f"✅ <b>Заявка на вывод одобрена!</b>\n\n"
            f"Номер заявки: #{withdrawal.id}\n"
            f"Сумма: {format_currency_amount(withdrawal.amount, withdrawal.currency)}\n\n"
        )

        if withdrawal.currency == CurrencyType.STARS:
            if total_refunded > 0 and remaining_amount == 0:
                # Full amount refunded automatically
                user_message += (
                    f"⭐ <b>Звезды возвращены!</b>\n"
                    f"Все {int(total_refunded)} звезд возвращены на ваш счет Telegram Stars автоматически."
                )
            elif total_refunded > 0 and remaining_amount > 0:
                # Partial refund
                user_message += (
                    f"⭐ <b>Частичный возврат выполнен</b>\n"
                    f"Автоматически возвращено: {int(total_refunded)} ⭐\n"
                    f"Остаток ({int(remaining_amount)} ⭐) будет отправлен администратором вручную в ближайшее время."
                )
            else:
                # No automatic refund possible
                user_message += (
                    f"⭐ Звезды будут отправлены администратором в виде подарка в ближайшее время.\n"
                    f"Сумма: {int(withdrawal.amount)} ⭐"
                )
        else:
            user_message += "💳 Средства будут переведены на указанные реквизиты в течение 1-3 рабочих дней."

        await notification_service.send_to_user(
            user.telegram_id,
            user_message
        )

        # Save refund information to withdrawal metadata
        if withdrawal.currency == CurrencyType.STARS and total_refunded > 0:
            withdrawal.payment_metadata = {
                "total_refunded": total_refunded,
                "remaining": remaining_amount,
                "refund_count": len(refund_result.get("successful_refunds", [])),
                "refund_rate": refund_result.get("refund_rate", 0),
                "refund_details": refund_result.get("successful_refunds", [])
            }
            await session.commit()

        response_text = (
            f"✅ <b>Заявка #{withdrawal.id} одобрена!</b>\n\n"
            f"Сумма {format_currency_amount(withdrawal.amount, withdrawal.currency)} "
            f"списана с баланса пользователя.\n\n"
        )

        if admin_note:
            response_text += f"{admin_note}\n\n"

        response_text += "Пользователь уведомлен."

        await callback.message.edit_text(
            response_text,
            reply_markup=admin_menu(),
            parse_mode="HTML"
        )

        logger.info(
            f"Admin approved withdrawal #{withdrawal.id}, "
            f"user_id={user.id}, amount={withdrawal.amount}, "
            f"auto_refunded={total_refunded}, remaining={remaining_amount}"
        )

    await callback.answer()


@router.callback_query(F.data.startswith("admin_reject_withdrawal_"))
async def callback_admin_reject_withdrawal(callback: CallbackQuery, state: FSMContext):
    """Reject withdrawal request"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    withdrawal_id = int(callback.data.split("_")[-1])

    async with get_session() as session:
        withdrawal = await crud.get_withdrawal_request(session, withdrawal_id)

        if not withdrawal:
            await callback.answer("Заявка не найдена", show_alert=True)
            return

        if withdrawal.status != WithdrawalStatus.PENDING:
            await callback.answer("Заявка уже обработана", show_alert=True)
            return

        # Get admin user for admin_id
        admin_user = await crud.get_user_by_telegram_id(session, callback.from_user.id)

        # Update withdrawal status
        await crud.update_withdrawal_status(
            session,
            withdrawal_id=withdrawal.id,
            status=WithdrawalStatus.REJECTED,
            admin_id=admin_user.id if admin_user else None,
            rejection_reason="Отклонено администратором"
        )

        await session.commit()

        # Notify user
        from app.services.notification import NotificationService
        bot = callback.bot
        notification_service = NotificationService(bot)

        user = withdrawal.user
        user_message = (
            f"❌ <b>Заявка на вывод отклонена</b>\n\n"
            f"Номер заявки: #{withdrawal.id}\n"
            f"Сумма: {format_currency_amount(withdrawal.amount, withdrawal.currency)}\n\n"
            f"Причина: Отклонено администратором\n\n"
            f"Средства остались на вашем балансе."
        )

        await notification_service.send_to_user(
            user.telegram_id,
            user_message
        )

        await callback.message.edit_text(
            f"❌ <b>Заявка #{withdrawal.id} отклонена</b>\n\n"
            f"Пользователь уведомлен.",
            reply_markup=admin_menu(),
            parse_mode="HTML"
        )

        logger.info(
            f"Admin rejected withdrawal #{withdrawal.id}, user_id={user.id}"
        )

    await callback.answer()


# ==================== PAYOUT CONFIRMATION HANDLERS ====================

@router.callback_query(F.data.startswith("confirm_payout:"))
async def callback_confirm_payout(callback: CallbackQuery):
    """Admin confirms that they paid the winner"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Только администратор может это сделать!", show_alert=True)
        return

    # Parse raffle ID from callback data
    raffle_id = int(callback.data.split(":")[1])

    async with get_session() as session:
        # Get payout request
        payout = await crud.get_payout_request_by_raffle(session, raffle_id)

        if not payout:
            await callback.answer("❌ Запрос на выплату не найден!", show_alert=True)
            return

        if payout.status == PayoutStatus.COMPLETED:
            await callback.answer("✅ Эта выплата уже подтверждена!", show_alert=True)
            return

        # Get admin user for tracking
        admin_user = await crud.get_user_by_telegram_id(session, callback.from_user.id)

        # Update payout status
        await crud.update_payout_status(
            session,
            payout_id=payout.id,
            status=PayoutStatus.COMPLETED,
            admin_id=admin_user.id if admin_user else None,
        )

        await session.commit()

        # Get winner info
        winner = payout.winner
        currency_symbol = "⭐" if payout.currency == CurrencyType.STARS else "₽"
        amount_str = f"{int(payout.amount)}" if payout.currency == CurrencyType.STARS else f"{payout.amount:.2f}"

    # Update admin message
    await callback.message.edit_text(
        f"✅ <b>ВЫПЛАТА ПОДТВЕРЖДЕНА</b>\n\n"
        f"🏆 Розыгрыш: #{raffle_id}\n"
        f"👤 Победитель: {winner.first_name}"
        f"{' @' + winner.username if winner.username else ''}\n"
        f"💰 Сумма: {amount_str} {currency_symbol}\n\n"
        f"<b>Статус:</b> Оплачено ✅\n"
        f"<b>Время:</b> {payout.completed_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"Победитель уведомлен о получении приза.",
        parse_mode="HTML"
    )
    await callback.answer("✅ Выплата подтверждена!")

    # Notify winner about completed payout
    from app.services.admin_payout_service import create_admin_payout_service
    payout_service = create_admin_payout_service(callback.bot)
    await payout_service.notify_winner_payment_completed(
        winner_id=winner.telegram_id,
        amount=payout.amount,
        raffle_id=raffle_id,
        currency=payout.currency,
    )

    logger.info(
        f"Payout confirmed by admin {callback.from_user.id} "
        f"for raffle {raffle_id}, winner {winner.telegram_id}"
    )


@router.callback_query(F.data.startswith("reject_payout:"))
async def callback_reject_payout(callback: CallbackQuery):
    """Admin rejects payout (requires reason)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Только администратор может это сделать!", show_alert=True)
        return

    # Parse raffle ID
    raffle_id = int(callback.data.split(":")[1])

    async with get_session() as session:
        # Get payout request
        payout = await crud.get_payout_request_by_raffle(session, raffle_id)

        if not payout:
            await callback.answer("❌ Запрос на выплату не найден!", show_alert=True)
            return

        if payout.status != PayoutStatus.PENDING:
            await callback.answer("❌ Эта выплата уже обработана!", show_alert=True)
            return

        # Get admin user
        admin_user = await crud.get_user_by_telegram_id(session, callback.from_user.id)

        # Update status to rejected with default reason
        await crud.update_payout_status(
            session,
            payout_id=payout.id,
            status=PayoutStatus.REJECTED,
            admin_id=admin_user.id if admin_user else None,
            rejection_reason="Отклонено администратором",
        )

        await session.commit()

        winner = payout.winner
        currency_symbol = "⭐" if payout.currency == CurrencyType.STARS else "₽"
        amount_str = f"{int(payout.amount)}" if payout.currency == CurrencyType.STARS else f"{payout.amount:.2f}"

    # Update message
    await callback.message.edit_text(
        f"❌ <b>ВЫПЛАТА ОТКЛОНЕНА</b>\n\n"
        f"🏆 Розыгрыш: #{raffle_id}\n"
        f"👤 Победитель: {winner.first_name}"
        f"{' @' + winner.username if winner.username else ''}\n"
        f"💰 Сумма: {amount_str} {currency_symbol}\n\n"
        f"<b>Статус:</b> Отклонено ❌\n"
        f"<b>Причина:</b> Отклонено администратором\n\n"
        f"⚠️ Необходимо повторно обработать этот платеж!",
        parse_mode="HTML",
        reply_markup=admin_menu()
    )

    await callback.answer("❌ Выплата отклонена")

    # Notify winner
    from app.services.notification import NotificationService
    notification_service = NotificationService(callback.bot)

    winner_message = (
        f"⚠️ <b>Проблема с выплатой приза</b>\n\n"
        f"Розыгрыш: #{raffle_id}\n"
        f"Сумма: {amount_str} {currency_symbol}\n\n"
        f"К сожалению, произошла проблема с выплатой.\n"
        f"Администратор свяжется с вами в ближайшее время для решения вопроса.\n\n"
        f"Приносим извинения за неудобства."
    )

    await notification_service.send_to_user(
        winner.telegram_id,
        winner_message
    )

    logger.warning(
        f"Payout rejected by admin {callback.from_user.id} "
        f"for raffle {raffle_id}, winner {winner.telegram_id}"
    )
