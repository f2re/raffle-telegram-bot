from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

from app.database.session import get_session
from app.database import crud
from app.database.models import CurrencyType, WithdrawalStatus
from app.config import settings
from app.keyboards.inline import back_button
from app.utils import validate_withdrawal_amount, format_currency_amount, round_rub_amount

router = Router()


class WithdrawalStates(StatesGroup):
    """States for withdrawal process"""
    waiting_for_currency = State()
    waiting_for_amount = State()
    waiting_for_card_number = State()
    waiting_for_phone_number = State()
    waiting_for_payment_method = State()


@router.callback_query(F.data == "balance")
async def callback_balance(callback: CallbackQuery):
    """Show user balance"""
    async with get_session() as session:
        user = await crud.get_user_by_telegram_id(session, callback.from_user.id)

        if not user:
            await callback.answer("Ошибка: пользователь не найден")
            return

        balance_text = (
            f"<b>💰 Ваш баланс</b>\n\n"
            f"⭐ Звезды: {int(user.balance_stars)}\n"
            f"₽ Рубли: {round_rub_amount(user.balance_rub)}\n\n"
            f"Для вывода средств используйте кнопку ниже"
        )

        from app.keyboards.inline import balance_keyboard
        await callback.message.edit_text(
            balance_text,
            reply_markup=balance_keyboard(),
            parse_mode="HTML"
        )

    await callback.answer()


@router.callback_query(F.data == "withdraw")
async def callback_withdraw(callback: CallbackQuery, state: FSMContext):
    """Start withdrawal process"""
    async with get_session() as session:
        user = await crud.get_user_by_telegram_id(session, callback.from_user.id)

        if not user:
            await callback.answer("Ошибка: пользователь не найден")
            return

        # Check if user has any balance
        if user.balance_stars == 0 and user.balance_rub == 0:
            await callback.answer(
                "У вас нет средств для вывода",
                show_alert=True
            )
            return

        balance_info = ""
        if user.balance_stars > 0:
            balance_info += f"⭐ Звезды: {int(user.balance_stars)}\n"
        if user.balance_rub > 0:
            balance_info += f"₽ Рубли: {round_rub_amount(user.balance_rub)}\n"

        await callback.message.edit_text(
            f"<b>💸 Вывод средств</b>\n\n"
            f"Ваш баланс:\n{balance_info}\n"
            f"Выберите валюту для вывода:\n"
            f"Отправьте 'stars' для звезд или 'rub' для рублей",
            parse_mode="HTML"
        )

        await state.set_state(WithdrawalStates.waiting_for_currency)

    await callback.answer()


@router.message(WithdrawalStates.waiting_for_currency)
async def process_withdrawal_currency(message: Message, state: FSMContext):
    """Process currency selection for withdrawal"""
    currency_text = message.text.lower().strip()

    if currency_text not in ["stars", "rub"]:
        await message.answer(
            "Пожалуйста, введите 'stars' или 'rub'"
        )
        return

    currency_type = CurrencyType.STARS if currency_text == "stars" else CurrencyType.RUB

    async with get_session() as session:
        user = await crud.get_user_by_telegram_id(session, message.from_user.id)

        if not user:
            await message.answer("Ошибка: пользователь не найден")
            await state.clear()
            return

        # Check balance
        balance = user.balance_stars if currency_type == CurrencyType.STARS else user.balance_rub

        if balance <= 0:
            await message.answer(
                f"Недостаточно средств для вывода в {currency_text}",
                reply_markup=back_button()
            )
            await state.clear()
            return

        # Store currency choice
        await state.update_data(currency=currency_type)

        # Get minimum withdrawal amount
        min_amount = (
            settings.MIN_WITHDRAWAL_STARS
            if currency_type == CurrencyType.STARS
            else settings.MIN_WITHDRAWAL_RUB
        )

        currency_symbol = "⭐" if currency_type == CurrencyType.STARS else "₽"

        withdrawal_info = f"<b>💸 Вывод {currency_symbol}</b>\n\n"
        withdrawal_info += f"Ваш баланс: {format_currency_amount(balance, currency_type)}\n"

        if currency_type == CurrencyType.STARS:
            withdrawal_info += f"Минимум для вывода: {format_currency_amount(min_amount, currency_type)}\n"
            withdrawal_info += (
                "\n⭐ <b>Умная система вывода:</b>\n"
                "Звезды возвращаются автоматически через ваши платежи (до 21 дня)\n"
                "Если нужно, остаток отправит администратор вручную\n"
            )
        else:
            withdrawal_info += f"Минимум для вывода: {format_currency_amount(min_amount, currency_type)}\n"

        withdrawal_info += "\nВведите сумму для вывода:"

        await message.answer(
            withdrawal_info,
            parse_mode="HTML"
        )

        await state.set_state(WithdrawalStates.waiting_for_amount)


@router.message(WithdrawalStates.waiting_for_amount)
async def process_withdrawal_amount(message: Message, state: FSMContext):
    """Process withdrawal amount"""
    try:
        amount = float(message.text.strip())
    except ValueError:
        await message.answer("Пожалуйста, введите число!")
        return

    data = await state.get_data()
    currency = data.get("currency")

    # Validate amount
    is_valid, error_msg = validate_withdrawal_amount(amount, currency)
    if not is_valid:
        await message.answer(f"❌ {error_msg}")
        return

    # Round rubles to whole numbers
    if currency == CurrencyType.RUB:
        amount = round_rub_amount(amount)

    async with get_session() as session:
        user = await crud.get_user_by_telegram_id(session, message.from_user.id)

        if not user:
            await message.answer("Ошибка: пользователь не найден")
            await state.clear()
            return

        # Check if user has enough balance
        balance = user.balance_stars if currency == CurrencyType.STARS else user.balance_rub

        if amount > balance:
            await message.answer(
                f"❌ Недостаточно средств!\n"
                f"Ваш баланс: {format_currency_amount(balance, currency)}",
                parse_mode="HTML"
            )
            return

        await state.update_data(amount=amount)

        # Ask for payment details based on currency
        if currency == CurrencyType.STARS:
            # For Stars, create withdrawal request immediately
            # (Stars withdrawal is handled automatically by Telegram)
            await create_withdrawal_request(message, state, session, user, message.bot)
        else:
            # For RUB, ask for payment method
            await message.answer(
                f"<b>💳 Способ получения</b>\n\n"
                f"Сумма: {format_currency_amount(amount, currency)}\n\n"
                f"Выберите способ получения:\n"
                f"1. Отправьте номер карты (16 цифр)\n"
                f"2. Отправьте номер телефона для СБП (например, +79001234567)",
                parse_mode="HTML"
            )
            await state.set_state(WithdrawalStates.waiting_for_payment_method)


@router.message(WithdrawalStates.waiting_for_payment_method)
async def process_payment_method(message: Message, state: FSMContext):
    """Process payment method (card or phone)"""
    text = message.text.strip().replace(" ", "").replace("-", "")

    # Check if it's a card number (16 digits)
    if text.isdigit() and len(text) == 16:
        await state.update_data(card_number=text)

        async with get_session() as session:
            user = await crud.get_user_by_telegram_id(session, message.from_user.id)
            await create_withdrawal_request(message, state, session, user, message.bot)

    # Check if it's a phone number
    elif text.startswith("+") and text[1:].isdigit() and len(text) >= 11:
        await state.update_data(phone_number=text)

        async with get_session() as session:
            user = await crud.get_user_by_telegram_id(session, message.from_user.id)
            await create_withdrawal_request(message, state, session, user, message.bot)

    else:
        await message.answer(
            "❌ Неверный формат!\n\n"
            "Отправьте:\n"
            "- Номер карты (16 цифр)\n"
            "- Номер телефона для СБП (например, +79001234567)"
        )


async def create_withdrawal_request(
    message: Message,
    state: FSMContext,
    session,
    user,
    bot
):
    """Create withdrawal request in database"""
    data = await state.get_data()
    currency = data.get("currency")
    amount = data.get("amount")
    card_number = data.get("card_number")
    phone_number = data.get("phone_number")

    try:
        # Create withdrawal request
        withdrawal = await crud.create_withdrawal_request(
            session,
            user_id=user.id,
            amount=amount,
            currency=currency,
            card_number=card_number,
            phone_number=phone_number,
        )

        await session.commit()

        # Format payment method for display
        payment_method = ""
        if card_number:
            # Mask card number (show only last 4 digits)
            masked_card = f"**** **** **** {card_number[-4:]}"
            payment_method = f"💳 Карта: {masked_card}"
        elif phone_number:
            payment_method = f"📱 Телефон: {phone_number}"
        else:
            payment_method = "⭐ Telegram Stars"

        withdrawal_message = (
            f"✅ <b>Заявка на вывод создана!</b>\n\n"
            f"Номер заявки: #{withdrawal.id}\n"
            f"Сумма: {format_currency_amount(amount, currency)}\n"
            f"{payment_method}\n\n"
        )

        if currency == CurrencyType.STARS:
            withdrawal_message += (
                "⭐ <b>Вывод звезд</b>\n"
                "Минимальная сумма: от 1 звезды!\n\n"
                "После одобрения администратором:\n"
                "• Система попытается автоматически вернуть звезды через ваши недавние платежи (до 21 дня)\n"
                "• Если полный автоматический возврат невозможен, остаток будет отправлен администратором вручную\n"
                "• Вы получите уведомление с деталями возврата\n\n"
            )

        withdrawal_message += (
            "Ваша заявка отправлена на рассмотрение администратору.\n"
            "Вы получите уведомление после проверки."
        )

        await message.answer(
            withdrawal_message,
            reply_markup=back_button(),
            parse_mode="HTML"
        )

        logger.info(
            f"Withdrawal request created: user_id={user.id}, "
            f"amount={amount}, currency={currency.value}, id={withdrawal.id}"
        )

        # Notify admin
        from app.services.notification import NotificationService
        notification_service = NotificationService(bot)

        admin_message = (
            f"🔔 <b>Новая заявка на вывод!</b>\n\n"
            f"ID заявки: #{withdrawal.id}\n"
            f"Пользователь: {user.first_name}"
        )
        if user.username:
            admin_message += f" (@{user.username})"

        admin_message += (
            f"\nСумма: {format_currency_amount(amount, currency)}\n"
            f"{payment_method}\n\n"
            f"Используйте /admin для просмотра заявок"
        )

        await notification_service.send_to_user(
            settings.ADMIN_USER_ID,
            admin_message
        )

    except Exception as e:
        logger.error(f"Failed to create withdrawal request: {e}", exc_info=True)
        await message.answer(
            "❌ Ошибка при создании заявки. Попробуйте позже.",
            reply_markup=back_button()
        )

    await state.clear()


@router.callback_query(F.data == "my_withdrawals")
async def callback_my_withdrawals(callback: CallbackQuery):
    """Show user's withdrawal history"""
    async with get_session() as session:
        user = await crud.get_user_by_telegram_id(session, callback.from_user.id)

        if not user:
            await callback.answer("Ошибка: пользователь не найден")
            return

        withdrawals = await crud.get_user_withdrawals(session, user.id, limit=10)

        if not withdrawals:
            await callback.message.edit_text(
                "<b>📜 История выводов</b>\n\n"
                "У вас пока нет заявок на вывод средств.",
                reply_markup=back_button(),
                parse_mode="HTML"
            )
            await callback.answer()
            return

        history_text = "<b>📜 История выводов</b>\n\n"

        for w in withdrawals:
            status_emoji = get_withdrawal_status_emoji(w.status)

            history_text += f"{status_emoji} Заявка #{w.id}\n"
            history_text += f"Сумма: {format_currency_amount(w.amount, w.currency)}\n"
            history_text += f"Статус: {w.status.value}\n"

            if w.status == WithdrawalStatus.REJECTED and w.rejection_reason:
                history_text += f"Причина: {w.rejection_reason}\n"

            history_text += f"Дата: {w.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"

        await callback.message.edit_text(
            history_text,
            reply_markup=back_button(),
            parse_mode="HTML"
        )

    await callback.answer()


def get_withdrawal_status_emoji(status: WithdrawalStatus) -> str:
    """Get emoji for withdrawal status"""
    emoji_map = {
        WithdrawalStatus.PENDING: "⏳",
        WithdrawalStatus.APPROVED: "✅",
        WithdrawalStatus.REJECTED: "❌",
        WithdrawalStatus.PROCESSING: "⚙️",
        WithdrawalStatus.COMPLETED: "✅",
        WithdrawalStatus.FAILED: "❌",
    }
    return emoji_map.get(status, "❓")
