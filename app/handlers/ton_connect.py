"""
TON Connect Handlers

Handles wallet connection/disconnection via TON Connect protocol
"""

import asyncio
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

from app.database.session import get_session
from app.database import crud
from app.services.ton_connect_service import ton_connect_service, TonConnectError
from app.keyboards.inline import ton_connect_keyboard, back_button

router = Router()


class TonConnectStates(StatesGroup):
    """States for TON Connect flow"""
    waiting_connection = State()


@router.callback_query(F.data == "connect_ton_wallet")
async def callback_connect_ton_wallet(callback: CallbackQuery, state: FSMContext):
    """
    Initiate TON Connect wallet connection

    Shows QR code and universal link for wallet connection
    """
    async with get_session() as session:
        # Get or create user
        user = await crud.get_or_create_user(
            session,
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
            last_name=callback.from_user.last_name,
        )

        # Check if wallet already connected
        existing_session = await crud.get_active_ton_connect_session(session, user.id)
        if existing_session:
            await callback.message.edit_text(
                f"🔗 <b>Кошелек уже подключен</b>\n\n"
                f"<b>Адрес:</b> <code>{existing_session.wallet_address}</code>\n\n"
                f"Для подключения другого кошелька сначала отключите текущий.",
                reply_markup=ton_connect_keyboard(
                    is_connected=True,
                    wallet_address=existing_session.wallet_address
                ),
                parse_mode="HTML"
            )
            await callback.answer()
            return

        await session.commit()

    try:
        # Generate connection URL
        connection_data = await ton_connect_service.get_connection_url(
            user_id=user.id,
            wallet_name="tonkeeper"
        )

        connection_url = connection_data["universal_url"]

        # Send QR code and connection instructions
        await callback.message.edit_text(
            f"🔗 <b>Подключение TON кошелька</b>\n\n"
            f"<b>Способ 1 (рекомендуем):</b>\n"
            f"Нажмите кнопку ниже - кошелек откроется автоматически\n\n"
            f"<b>Способ 2 (QR код):</b>\n"
            f"Откройте Tonkeeper → Настройки → TON Connect → Сканировать QR\n\n"
            f"💡 После подключения кошелька вы сможете оплачивать участие в розыгрышах "
            f"в один клик - без копирования адресов и комментариев!\n\n"
            f"⏳ Ожидаю подключения кошелька...",
            reply_markup=ton_connect_keyboard(
                is_connected=False,
                connection_url=connection_url
            ),
            parse_mode="HTML"
        )

        await callback.answer()

        # Set state to waiting for connection
        await state.set_state(TonConnectStates.waiting_connection)

        # Start listening for connection in background
        asyncio.create_task(
            wait_for_connection(
                callback.message,
                user.id,
                callback.from_user.id,
                state
            )
        )

    except TonConnectError as e:
        logger.error(f"Failed to generate connection URL: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка подключения</b>\n\n"
            f"Не удалось создать ссылку для подключения кошелька.\n"
            f"Попробуйте позже или свяжитесь с поддержкой.\n\n"
            f"Код ошибки: {str(e)[:100]}",
            reply_markup=back_button(),
            parse_mode="HTML"
        )
        await callback.answer()


async def wait_for_connection(
    message: Message,
    user_id: int,
    telegram_id: int,
    state: FSMContext
):
    """
    Wait for wallet connection (background task)

    Args:
        message: Message to update
        user_id: User ID (from database)
        telegram_id: Telegram user ID
        state: FSM state
    """
    try:
        # Listen for connection (5 minutes timeout)
        wallet_info = await ton_connect_service.listen_for_connection(
            user_id=user_id,
            timeout=300
        )

        if wallet_info:
            # Connection successful
            await message.edit_text(
                f"✅ <b>Кошелек успешно подключен!</b>\n\n"
                f"<b>Адрес:</b> <code>{wallet_info['address']}</code>\n\n"
                f"Теперь вы можете оплачивать участие в розыгрышах в один клик!\n"
                f"Бот будет автоматически отправлять запросы на оплату в ваш кошелек.",
                reply_markup=ton_connect_keyboard(
                    is_connected=True,
                    wallet_address=wallet_info['address']
                ),
                parse_mode="HTML"
            )

            logger.info(
                f"Wallet connected successfully for user {telegram_id}: "
                f"{wallet_info['address'][:8]}..."
            )
        else:
            # Connection timeout
            await message.edit_text(
                f"⏱ <b>Время подключения истекло</b>\n\n"
                f"Вы не подключили кошелек в течение 5 минут.\n"
                f"Попробуйте еще раз, когда будете готовы.",
                reply_markup=back_button(),
                parse_mode="HTML"
            )

        # Clear state
        await state.clear()

    except Exception as e:
        logger.error(f"Error waiting for connection: {e}", exc_info=True)
        await message.edit_text(
            f"❌ <b>Ошибка подключения</b>\n\n"
            f"Произошла ошибка при подключении кошелька.\n"
            f"Попробуйте позже.",
            reply_markup=back_button(),
            parse_mode="HTML"
        )
        await state.clear()


@router.callback_query(F.data == "disconnect_ton_wallet")
async def callback_disconnect_ton_wallet(callback: CallbackQuery):
    """Disconnect TON wallet"""
    async with get_session() as session:
        # Get user
        user = await crud.get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("Ошибка: пользователь не найден", show_alert=True)
            return

        # Check if wallet connected
        existing_session = await crud.get_active_ton_connect_session(session, user.id)
        if not existing_session:
            await callback.answer("Кошелек не подключен", show_alert=True)
            return

        wallet_address = existing_session.wallet_address

    # Disconnect wallet
    success = await ton_connect_service.disconnect_wallet(user.id)

    if success:
        await callback.message.edit_text(
            f"✅ <b>Кошелек отключен</b>\n\n"
            f"Кошелек <code>{wallet_address[:8]}...{wallet_address[-4:]}</code> "
            f"успешно отключен.\n\n"
            f"Вы можете подключить его снова в любое время.",
            reply_markup=back_button(),
            parse_mode="HTML"
        )

        logger.info(f"Wallet disconnected for user {callback.from_user.id}")
    else:
        await callback.answer(
            "Ошибка отключения кошелька. Попробуйте позже.",
            show_alert=True
        )

    await callback.answer()


@router.callback_query(F.data == "check_ton_connection")
async def callback_check_ton_connection(callback: CallbackQuery):
    """Check TON Connect connection status"""
    async with get_session() as session:
        # Get user
        user = await crud.get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("Ошибка: пользователь не найден", show_alert=True)
            return

        # Check connection
        existing_session = await crud.get_active_ton_connect_session(session, user.id)

    if existing_session:
        await callback.answer(
            f"✅ Кошелек подключен\n{existing_session.wallet_address[:8]}...",
            show_alert=True
        )
    else:
        await callback.answer(
            "❌ Кошелек не подключен",
            show_alert=True
        )


@router.callback_query(F.data == "ton_wallet_info")
async def callback_ton_wallet_info(callback: CallbackQuery):
    """Show TON wallet connection info"""
    async with get_session() as session:
        # Get user
        user = await crud.get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("Ошибка: пользователь не найден", show_alert=True)
            return

        # Get session
        ton_session = await crud.get_active_ton_connect_session(session, user.id)

        if not ton_session:
            await callback.message.edit_text(
                f"🔗 <b>TON Connect</b>\n\n"
                f"Кошелек не подключен.\n\n"
                f"<b>Что дает подключение кошелька:</b>\n"
                f"• Оплата в 1 клик без копирования адресов\n"
                f"• Автоматическое открытие кошелька для подтверждения\n"
                f"• Безопасность - транзакции подписываются в вашем кошельке\n"
                f"• Удобство - один раз подключил и всегда готов\n\n"
                f"Нажмите кнопку ниже, чтобы подключить кошелек.",
                reply_markup=ton_connect_keyboard(is_connected=False),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                f"🔗 <b>TON Connect</b>\n\n"
                f"<b>Статус:</b> ✅ Подключен\n"
                f"<b>Адрес:</b> <code>{ton_session.wallet_address}</code>\n"
                f"<b>Подключен:</b> {ton_session.connected_at.strftime('%d.%m.%Y %H:%M')}\n"
                f"<b>Последнее использование:</b> {ton_session.last_used.strftime('%d.%m.%Y %H:%M')}\n\n"
                f"Теперь вы можете оплачивать участие в розыгрышах в один клик!",
                reply_markup=ton_connect_keyboard(
                    is_connected=True,
                    wallet_address=ton_session.wallet_address
                ),
                parse_mode="HTML"
            )

    await callback.answer()
