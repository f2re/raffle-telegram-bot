from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from loguru import logger

from app.database.session import get_session
from app.database import crud
from app.keyboards.inline import main_menu, back_button
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

    # Adjust message based on STARS_ONLY mode
    payment_text = "⭐" if settings.STARS_ONLY else "звездами или рублями"

    welcome_text = (
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Добро пожаловать в бот розыгрыша призов!\n\n"
        "🎁 <b>Как это работает:</b>\n"
        "1. Присоединяйся к текущему розыгрышу\n"
        f"2. Оплачиваешь взнос ({payment_text})\n"
        "3. Когда соберется минимальное количество участников - запускаем розыгрыш\n"
        "4. Победитель получает призовой фонд!\n\n"
        "✨ Все розыгрыши честные и проверяемые через Random.org\n"
        "📊 Прозрачная статистика и история\n\n"
        "Выбери действие ниже:"
    )

    await message.answer(welcome_text, reply_markup=main_menu(), parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command"""
    help_text = (
        "<b>📖 Помощь</b>\n\n"
        "<b>Доступные команды:</b>\n"
        "/start - Главное меню\n"
        "/balance - Показать баланс\n"
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

        # Show only stars if STARS_ONLY mode is enabled
        if settings.STARS_ONLY:
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

        await message.answer(balance_text, reply_markup=back_button(), parse_mode="HTML")


@router.callback_query(F.data == "balance")
async def callback_balance(callback: CallbackQuery):
    """Handle balance button"""
    async with get_session() as session:
        user = await crud.get_user_by_telegram_id(session, callback.from_user.id)

        if not user:
            await callback.answer("Ошибка: пользователь не найден")
            return

        # Show only stars if STARS_ONLY mode is enabled
        if settings.STARS_ONLY:
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
            reply_markup=back_button(),
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data == "rules")
async def callback_rules(callback: CallbackQuery):
    """Handle rules button"""
    # Adjust rules based on STARS_ONLY mode
    if settings.STARS_ONLY:
        entry_fee_text = f"⭐ {settings.STARS_ENTRY_FEE} звезд"
        payout_text = "Победитель получает приз автоматически ⭐"
    else:
        entry_fee_text = f"⭐ {settings.STARS_ENTRY_FEE} звезд или 💳 {settings.RUB_ENTRY_FEE} рублей"
        payout_text = (
            "Победитель получает приз автоматически\n"
            "Звезды - мгновенно\n"
            "Рубли - в течение нескольких минут"
        )

    rules_text = (
        "<b>📜 Правила участия</b>\n\n"
        "<b>1. Вступительный взнос:</b>\n"
        f"{entry_fee_text}\n\n"
        "<b>2. Минимум участников:</b>\n"
        "Розыгрыш стартует при наборе минимального количества участников\n\n"
        "<b>3. Призовой фонд:</b>\n"
        "80-90% от общей суммы взносов\n"
        "Комиссия идет на поддержку бота\n\n"
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
    # Adjust message based on STARS_ONLY mode
    payment_text = "⭐" if settings.STARS_ONLY else "звездами или рублями"

    welcome_text = (
        f"Привет, {callback.from_user.first_name}! 👋\n\n"
        "Добро пожаловать в бот розыгрыша призов!\n\n"
        "🎁 <b>Как это работает:</b>\n"
        "1. Присоединяйся к текущему розыгрышу\n"
        f"2. Оплачиваешь взнос ({payment_text})\n"
        "3. Когда соберется минимальное количество участников - запускаем розыгрыш\n"
        "4. Победитель получает призовой фонд!\n\n"
        "✨ Все розыгрыши честные и проверяемые через Random.org\n"
        "📊 Прозрачная статистика и история\n\n"
        "Выбери действие ниже:"
    )

    await callback.message.edit_text(
        welcome_text,
        reply_markup=main_menu(),
        parse_mode="HTML"
    )
    await callback.answer()
