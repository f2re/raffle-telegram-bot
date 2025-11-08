from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

from app.database.session import get_session
from app.database import crud
from app.database.models import CurrencyType, RaffleStatus
from app.config import settings
from app.keyboards.inline import admin_menu, confirm_raffle_start, back_button
from app.handlers.raffle import execute_raffle

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
        f"Для изменения настроек отредактируйте .env файл"
    )

    await callback.message.edit_text(
        settings_text,
        reply_markup=admin_menu(),
        parse_mode="HTML"
    )

    await callback.answer()
