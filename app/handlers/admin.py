from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

from app.database.session import get_session
from app.database import crud
from app.database.models import CurrencyType, RaffleStatus, WithdrawalStatus
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
            user_message += "⭐ Средства будут возвращены на ваш счет Telegram Stars в течение 1-3 дней."
        else:
            user_message += "💳 Средства будут переведены на указанные реквизиты в течение 1-3 рабочих дней."

        await notification_service.send_to_user(
            user.telegram_id,
            user_message
        )

        await callback.message.edit_text(
            f"✅ <b>Заявка #{withdrawal.id} одобрена!</b>\n\n"
            f"Сумма {format_currency_amount(withdrawal.amount, withdrawal.currency)} "
            f"списана с баланса пользователя.\n\n"
            f"Пользователь уведомлен.",
            reply_markup=admin_menu(),
            parse_mode="HTML"
        )

        logger.info(
            f"Admin approved withdrawal #{withdrawal.id}, "
            f"user_id={user.id}, amount={withdrawal.amount}"
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
