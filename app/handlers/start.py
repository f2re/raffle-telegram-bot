from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from loguru import logger

from app.database.session import get_session
from app.database import crud
from app.keyboards.inline import main_menu, back_button, balance_keyboard
from app.config import settings

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command"""
    async with get_session() as session:
        user = await crud.get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
        logger.info(f"User {user.telegram_id} started the bot")

    # Adjust message based on payment mode
    if settings.TON_ONLY:
        payment_text = f"💎 TON криптовалютой ({settings.TON_ENTRY_FEE} TON)"
        payment_benefits = (
            "💎 Оплата через TON блокчейн\n"
            "⚡️ Мгновенная обработка платежей\n"
            "🔐 Полная прозрачность транзакций\n"
            "🎁 Автоматическая выплата призов"
        )
    elif settings.STARS_ONLY:
        payment_text = "⭐ звездами Telegram"
        payment_benefits = "⭐ Telegram Stars\n🎯 Удобная интеграция"
    else:
        payment_text = "звездами или рублями"
        payment_benefits = "⭐ Telegram Stars или 💳 Рубли\n🎯 Выбор способа оплаты"

    welcome_text = (
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Добро пожаловать в бот розыгрыша призов!\n\n"
        "🎁 <b>Как это работает:</b>\n"
        "1. Присоединяйся к текущему розыгрышу\n"
        f"2. Оплачиваешь взнос ({payment_text})\n"
        "3. Когда соберется минимальное количество участников - запускаем розыгрыш\n"
        "4. Победитель получает призовой фонд!\n\n"
        f"{payment_benefits}\n\n"
        "✨ Все розыгрыши честные и проверяемые через Random.org\n\n"
        "Выбери действие ниже:"
    )

    await message.answer(welcome_text, reply_markup=main_menu(), parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command"""
    help_text = (
        "<b>❓ Помощь</b>\n\n"
        "<b>Доступные команды:</b>\n"
        "/start - Главное меню\n"
        "/balance - Показать баланс\n"
        "/raffle - Текущий розыгрыш\n"
        "/history - История участия\n"
        "/help - Эта справка\n\n"
        "<b>Как участвовать:</b>\n"
        "1. Нажми 'Участвовать в розыгрыше'\n"
        "2. Выбери способ оплаты\n"
        "3. Оплати взнос\n"
        "4. Жди результатов!\n\n"
        "<b>Честность:</b>\n"
        "Победитель определяется с помощью Random.org API.\n"
        "Каждый розыгрыш можно проверить по специальной ссылке.\n\n"
        "Удачи! 🍀"
    )

    await message.answer(help_text, reply_markup=back_button(), parse_mode="HTML")


@router.message(Command("balance"))
async def cmd_balance(message: Message):
    """Handle /balance command"""
    async with get_session() as session:
        user = await crud.get_user_by_telegram_id(session, message.from_user.id)

        if not user:
            await message.answer("Вы не зарегистрированы. Используйте /start")
            return

        # Show balance based on mode
        if settings.TON_ONLY:
            balance_text = (
                f"<b>💰 Ваш баланс:</b>\n\n"
                f"💎 TON: {user.balance_ton:.4f}\n\n"
            )
            if user.ton_wallet_address:
                balance_text += f"Кошелек: <code>{user.ton_wallet_address[:8]}...{user.ton_wallet_address[-6:]}</code>"
            else:
                balance_text += "⚠️ Укажите TON кошелек для получения призов!"
        elif settings.STARS_ONLY:
            balance_text = (
                f"<b>💰 Ваш баланс:</b>\n\n"
                f"⭐ Звезды: {int(user.balance_stars)}"
            )
        else:
            balance_text = (
                f"<b>💰 Ваш баланс:</b>\n\n"
                f"⭐ Звезды: {int(user.balance_stars)}\n"
                f"💳 Рубли: {user.balance_rub:.2f} RUB"
            )

        await message.answer(balance_text, reply_markup=balance_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "balance")
async def callback_balance(callback: CallbackQuery):
    """Handle balance button"""
    async with get_session() as session:
        user = await crud.get_user_by_telegram_id(session, callback.from_user.id)

        if not user:
            await callback.answer("Ошибка: пользователь не найден")
            return

        # Show balance based on mode
        if settings.TON_ONLY:
            balance_text = (
                f"<b>💰 Ваш баланс:</b>\n\n"
                f"💎 TON: {user.balance_ton:.4f}\n\n"
            )
            if user.ton_wallet_address:
                balance_text += f"Кошелек: <code>{user.ton_wallet_address[:8]}...{user.ton_wallet_address[-6:]}</code>"
            else:
                balance_text += "⚠️ Укажите TON кошелек для получения призов!"
        elif settings.STARS_ONLY:
            balance_text = (
                f"<b>💰 Ваш баланс:</b>\n\n"
                f"⭐ Звезды: {int(user.balance_stars)}"
            )
        else:
            balance_text = (
                f"<b>💰 Ваш баланс:</b>\n\n"
                f"⭐ Звезды: {int(user.balance_stars)}\n"
                f"💳 Рубли: {user.balance_rub:.2f} RUB"
            )

        await callback.message.edit_text(
            balance_text,
            reply_markup=balance_keyboard(),
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery):
    """Handle help button"""
    help_text = (
        "<b>❓ Помощь</b>\n\n"
        "<b>Доступные команды:</b>\n"
        "/start - Главное меню\n"
        "/balance - Показать баланс\n"
        "/raffle - Текущий розыгрыш\n"
        "/history - История участия\n"
        "/help - Эта справка\n\n"
        "<b>Как участвовать:</b>\n"
        "1. Нажми 'Участвовать в розыгрыше'\n"
        "2. Выбери способ оплаты\n"
        "3. Оплати взнос\n"
        "4. Жди результатов!\n\n"
        "<b>Честность:</b>\n"
        "Победитель определяется с помощью Random.org API.\n"
        "Каждый розыгрыш можно проверить по специальной ссылке.\n\n"
        "Удачи! 🍀"
    )

    await callback.message.edit_text(
        help_text,
        reply_markup=back_button(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "rules")
async def callback_rules(callback: CallbackQuery):
    """Handle rules button"""
    # Adjust rules based on payment mode
    if settings.TON_ONLY:
        entry_fee_text = f"💎 {settings.TON_ENTRY_FEE} TON"
        commission_text = f"{settings.TON_COMMISSION_PERCENT}%"
        payout_text = (
            "Победитель получает приз <b>автоматически на TON кошелек</b>\n"
            "⚡️ Выплата в течение нескольких секунд!\n"
            "🔗 Все транзакции проверяемы в блокчейне"
        )
    elif settings.STARS_ONLY:
        entry_fee_text = f"⭐ {settings.STARS_ENTRY_FEE} звезд"
        commission_text = f"{settings.STARS_COMMISSION_PERCENT}%"
        payout_text = "Победитель получает приз автоматически ⭐"
    else:
        entry_fee_text = f"⭐ {settings.STARS_ENTRY_FEE} звезд или 💳 {settings.RUB_ENTRY_FEE} рублей"
        commission_text = "15-20%"
        payout_text = (
            "Победитель получает приз автоматически\n"
            "Звезды - мгновенно\n"
            "Рубли - в течение нескольких минут"
        )

    rules_text = (
        "<b>ℹ️ Правила участия</b>\n\n"
        "<b>1. Вступительный взнос:</b>\n"
        f"{entry_fee_text}\n\n"
        "<b>2. Минимум участников:</b>\n"
        f"Розыгрыш стартует при наборе {settings.MIN_PARTICIPANTS} участников\n\n"
        "<b>3. Призовой фонд:</b>\n"
        f"Комиссия бота: {commission_text}\n"
        f"Приз победителю: {100 - (settings.TON_COMMISSION_PERCENT if settings.TON_ONLY else settings.STARS_COMMISSION_PERCENT)}%\n\n"
        "<b>4. Определение победителя:</b>\n"
        "Случайное число генерируется через Random.org\n"
        "Результат подписан криптографически и проверяем\n\n"
        "<b>5. Выплата приза:</b>\n"
        f"{payout_text}\n\n"
        "<b>✨ Честность гарантирована!</b>\n"
        "Каждый розыгрыш можно проверить по ссылке."
    )

    await callback.message.edit_text(
        rules_text,
        reply_markup=back_button(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_menu")
async def callback_back_to_menu(callback: CallbackQuery):
    """Handle back to menu button"""
    # Adjust message based on payment mode
    if settings.TON_ONLY:
        payment_text = f"💎 TON криптовалютой ({settings.TON_ENTRY_FEE} TON)"
        payment_benefits = (
            "💎 Оплата через TON блокчейн\n"
            "⚡️ Мгновенная обработка платежей\n"
            "🔐 Полная прозрачность транзакций\n"
            "🎁 Автоматическая выплата призов"
        )
    elif settings.STARS_ONLY:
        payment_text = "⭐ звездами Telegram"
        payment_benefits = "⭐ Telegram Stars\n🎯 Удобная интеграция"
    else:
        payment_text = "звездами или рублями"
        payment_benefits = "⭐ Telegram Stars или 💳 Рубли\n🎯 Выбор способа оплаты"

    welcome_text = (
        f"Привет, {callback.from_user.first_name}! 👋\n\n"
        "Добро пожаловать в бот розыгрыша призов!\n\n"
        "🎁 <b>Как это работает:</b>\n"
        "1. Присоединяйся к текущему розыгрышу\n"
        f"2. Оплачиваешь взнос ({payment_text})\n"
        "3. Когда соберется минимальное количество участников - запускаем розыгрыш\n"
        "4. Победитель получает призовой фонд!\n\n"
        f"{payment_benefits}\n\n"
        "✨ Все розыгрыши честные и проверяемые через Random.org\n\n"
        "Выбери действие ниже:"
    )

    await callback.message.edit_text(
        welcome_text,
        reply_markup=main_menu(),
        parse_mode="HTML"
    )
    await callback.answer()
