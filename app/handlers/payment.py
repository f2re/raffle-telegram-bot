from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice
from loguru import logger

from app.database.session import get_session
from app.database import crud
from app.database.models import CurrencyType, TransactionType, TransactionStatus
from app.config import settings
from app.services.payment_service import yookassa_service, PaymentError
from app.services.ton_service import ton_service
from app.services.ton_connect_service import ton_connect_service, TonConnectError
from app.keyboards.inline import (
    back_button, ton_payment_keyboard, ton_payment_choice_keyboard, ton_connect_keyboard
)

router = Router()


@router.callback_query(F.data == "pay_stars")
async def callback_pay_stars(callback: CallbackQuery):
    """Handle payment with Telegram Stars"""
    async with get_session() as session:
        # Get current raffle
        raffle = await crud.get_active_raffle(session)
        if not raffle:
            await callback.answer("Нет активного розыгрыша", show_alert=True)
            return

        # Check if already participating
        user = await crud.get_user_by_telegram_id(session, callback.from_user.id)
        participants = await crud.get_raffle_participants(session, raffle.id)

        if user and any(p.user_id == user.id for p in participants):
            await callback.answer("Вы уже участвуете в этом розыгрыше!", show_alert=True)
            return

    # Create invoice for Stars payment
    prices = [LabeledPrice(label="Участие в розыгрыше", amount=settings.STARS_ENTRY_FEE)]

    await callback.message.answer_invoice(
        title="Участие в розыгрыше",
        description="Оплата взноса звездами Telegram",
        payload=f"raffle_{raffle.id}",
        currency="XTR",  # Telegram Stars currency code
        prices=prices,
        provider_token="",  # Empty for Stars
    )

    await callback.answer()


@router.callback_query(F.data == "pay_rub")
async def callback_pay_rub(callback: CallbackQuery):
    """Handle payment with Russian Rubles via YooKassa"""
    if not yookassa_service.enabled:
        await callback.answer(
            "Оплата рублями временно недоступна",
            show_alert=True
        )
        return

    async with get_session() as session:
        # Get current raffle
        raffle = await crud.get_active_raffle(session)
        if not raffle:
            await callback.answer("Нет активного розыгрыша", show_alert=True)
            return

        # Check if already participating
        user = await crud.get_user_by_telegram_id(session, callback.from_user.id)
        participants = await crud.get_raffle_participants(session, raffle.id)

        if user and any(p.user_id == user.id for p in participants):
            await callback.answer("Вы уже участвуете в этом розыгрыше!", show_alert=True)
            return

        # Create transaction
        transaction = await crud.create_transaction(
            session,
            user_id=user.id,
            type=TransactionType.RAFFLE_ENTRY,
            amount=settings.RUB_ENTRY_FEE,
            currency=CurrencyType.RUB,
            description=f"Участие в розыгрыше #{raffle.id}",
            payment_metadata={"raffle_id": raffle.id}
        )

        try:
            # Create YooKassa payment
            payment_data = yookassa_service.create_payment(
                amount=settings.RUB_ENTRY_FEE,
                description=f"Участие в розыгрыше #{raffle.id}",
                user_id=user.id,
            )

            # Update transaction with payment ID
            transaction.payment_id = payment_data["payment_id"]
            await session.commit()

            # Send payment link
            await callback.message.answer(
                f"💳 <b>Оплата рублями</b>\n\n"
                f"Сумма: {settings.RUB_ENTRY_FEE} RUB\n\n"
                f"Нажмите кнопку ниже для оплаты:",
                reply_markup=back_button(),
                parse_mode="HTML"
            )

            # Send payment URL
            await callback.message.answer(
                f"🔗 Ссылка для оплаты:\n{payment_data['confirmation_url']}"
            )

            logger.info(
                f"Created RUB payment for user {user.telegram_id}, "
                f"payment_id: {payment_data['payment_id']}"
            )

        except PaymentError as e:
            logger.error(f"Payment creation failed: {e}")
            await crud.update_transaction_status(
                session, transaction.id, TransactionStatus.FAILED
            )
            await callback.answer(
                "Ошибка создания платежа. Попробуйте позже.",
                show_alert=True
            )

    await callback.answer()


@router.callback_query(F.data == "pay_ton")
async def callback_pay_ton(callback: CallbackQuery):
    """
    Handle payment with TON cryptocurrency

    Shows payment choice: TON Connect (if wallet connected) or Deep Links
    """
    async with get_session() as session:
        # Get current raffle
        raffle = await crud.get_active_raffle(session)
        if not raffle:
            await callback.answer("Нет активного розыгрыша", show_alert=True)
            return

        # Check if raffle uses TON
        if raffle.entry_fee_type != CurrencyType.TON:
            await callback.answer(
                "Этот розыгрыш не использует TON оплату",
                show_alert=True
            )
            return

        # Check if already participating
        user = await crud.get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            # Create user if doesn't exist
            user = await crud.get_or_create_user(
                session,
                telegram_id=callback.from_user.id,
                username=callback.from_user.username,
                first_name=callback.from_user.first_name,
                last_name=callback.from_user.last_name,
            )

        participants = await crud.get_raffle_participants(session, raffle.id)

        if user and any(p.user_id == user.id for p in participants):
            await callback.answer("Вы уже участвуете в этом розыгрыше!", show_alert=True)
            return

        # Check if TON Connect wallet is connected
        ton_session = await crud.get_active_ton_connect_session(session, user.id)
        is_wallet_connected = ton_session is not None

        # Get entry fee
        entry_fee = raffle.entry_fee_amount

        if is_wallet_connected:
            # Show TON Connect payment option
            await callback.message.edit_text(
                f"💎 <b>Оплата участия в розыгрыше #{raffle.id}</b>\n\n"
                f"<b>Сумма:</b> {entry_fee:.4f} TON\n\n"
                f"🔗 <b>У вас подключен кошелек TON Connect</b>\n"
                f"<code>{ton_session.wallet_address[:8]}...{ton_session.wallet_address[-4:]}</code>\n\n"
                f"⚡ <b>Быстрая оплата (рекомендуем):</b>\n"
                f"Нажмите кнопку ниже - кошелек откроется автоматически с готовой транзакцией!\n\n"
                f"💎 <b>Или оплатите вручную:</b>\n"
                f"Используйте стандартный способ с deep links",
                reply_markup=ton_payment_choice_keyboard(
                    is_wallet_connected=True,
                    raffle_id=raffle.id,
                    entry_fee=entry_fee
                ),
                parse_mode="HTML"
            )
        else:
            # Show Deep Links payment (fallback)
            await show_ton_deep_link_payment(callback, raffle, user)

        logger.info(
            f"TON payment screen sent to user {user.telegram_id} "
            f"for raffle {raffle.id} (wallet_connected={is_wallet_connected})"
        )

    await callback.answer()


async def show_ton_deep_link_payment(callback: CallbackQuery, raffle, user):
    """Show TON payment via deep links (fallback method)"""
    # Generate unique payment comment
    payment_comment = ton_service.generate_payment_comment(
        raffle_id=raffle.id,
        user_id=user.id
    )

    # Get entry fee
    entry_fee = raffle.entry_fee_amount

    # Generate deep links for different wallets
    deep_links = ton_service.generate_payment_deep_link(
        amount_ton=entry_fee,
        comment=payment_comment
    )

    # Send payment instructions with deep link buttons
    await callback.message.edit_text(
        f"💎 <b>Оплата участия в розыгрыше #{raffle.id}</b>\n\n"
        f"<b>Сумма:</b> {entry_fee:.4f} TON\n\n"
        f"🚀 <b>Быстрая оплата:</b>\n"
        f"Нажмите кнопку ниже - ваш TON кошелек откроется автоматически "
        f"с уже заполненной суммой и комментарием!\n\n"
        f"✅ После оплаты бот автоматически зарегистрирует ваше участие "
        f"в течение {settings.TON_TRANSACTION_CHECK_INTERVAL} секунд.\n\n"
        f"💡 <b>Совет:</b> Используйте кнопку '🔄 Проверить оплату' чтобы "
        f"узнать статус обработки платежа.",
        reply_markup=ton_payment_keyboard(
            tonkeeper_url=deep_links["tonkeeper"],
            ton_url=deep_links["ton"],
            raffle_id=raffle.id
        ),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("check_ton_payment_"))
async def callback_check_ton_payment(callback: CallbackQuery):
    """Check TON payment status"""
    raffle_id = int(callback.data.split("_")[3])

    async with get_session() as session:
        # Get user
        user = await crud.get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer(
                "Ошибка: пользователь не найден",
                show_alert=True
            )
            return

        # Check if user is already participating
        participants = await crud.get_raffle_participants(session, raffle_id)
        if any(p.user_id == user.id for p in participants):
            await callback.answer(
                "✅ Оплата получена! Вы уже участвуете в розыгрыше!",
                show_alert=True
            )
            return

        # Check if user has a pending transaction for this raffle
        # (transaction exists but user not yet added as participant)
        await callback.answer(
            "⏳ Платеж еще не обработан.\n\n"
            f"Обработка занимает до {settings.TON_TRANSACTION_CHECK_INTERVAL} секунд после отправки.\n"
            "Если вы только что отправили - подождите немного и проверьте снова.",
            show_alert=True
        )

    logger.info(
        f"User {callback.from_user.id} checked payment status for raffle {raffle_id}"
    )


@router.callback_query(F.data.startswith("show_manual_ton_payment_"))
async def callback_show_manual_ton_payment(callback: CallbackQuery):
    """Show manual payment details for users who can't use deep links"""
    raffle_id = int(callback.data.split("_")[4])

    async with get_session() as session:
        # Get raffle
        raffle = await crud.get_raffle_by_id(session, raffle_id)
        if not raffle:
            await callback.answer("Розыгрыш не найден", show_alert=True)
            return

        # Get user
        user = await crud.get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("Ошибка: пользователь не найден", show_alert=True)
            return

        # Generate payment comment
        payment_comment = ton_service.generate_payment_comment(
            raffle_id=raffle.id,
            user_id=user.id
        )

        # Get entry fee
        entry_fee = raffle.entry_fee_amount

        # Generate deep links again (for "back" navigation)
        deep_links = ton_service.generate_payment_deep_link(
            amount_ton=entry_fee,
            comment=payment_comment
        )

        # Show manual payment instructions
        await callback.message.edit_text(
            f"📋 <b>Данные для ручного ввода</b>\n\n"
            f"Если автоматическое открытие кошелька не работает, "
            f"введите данные вручную:\n\n"
            f"<b>Адрес получателя:</b>\n"
            f"<code>{settings.TON_WALLET_ADDRESS}</code>\n\n"
            f"<b>Сумма:</b>\n"
            f"<code>{entry_fee:.4f}</code> TON\n\n"
            f"<b>Комментарий (ОБЯЗАТЕЛЬНО):</b>\n"
            f"<code>{payment_comment}</code>\n\n"
            f"⚠️ <b>ВАЖНО:</b>\n"
            f"• Без комментария платеж не будет обработан\n"
            f"• Скопируйте комментарий точно как указано\n"
            f"• Отправьте точную сумму {entry_fee:.4f} TON\n\n"
            f"✅ После отправки платеж обработается автоматически "
            f"в течение {settings.TON_TRANSACTION_CHECK_INTERVAL} секунд.\n\n"
            f"💡 Для проверки статуса используйте кнопку '🔄 Проверить оплату'",
            reply_markup=ton_payment_keyboard(
                tonkeeper_url=deep_links["tonkeeper"],
                ton_url=deep_links["ton"],
                raffle_id=raffle.id
            ),
            parse_mode="HTML"
        )

    await callback.answer()

    logger.info(
        f"Manual payment details shown to user {callback.from_user.id} "
        f"for raffle {raffle_id}"
    )


@router.callback_query(F.data.startswith("pay_ton_connect_"))
async def callback_pay_ton_connect(callback: CallbackQuery):
    """Handle payment via TON Connect (connected wallet)"""
    raffle_id = int(callback.data.split("_")[3])

    async with get_session() as session:
        # Get raffle
        raffle = await crud.get_raffle_by_id(session, raffle_id)
        if not raffle:
            await callback.answer("Розыгрыш не найден", show_alert=True)
            return

        # Get user
        user = await crud.get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("Ошибка: пользователь не найден", show_alert=True)
            return

        # Check if wallet connected
        ton_session = await crud.get_active_ton_connect_session(session, user.id)
        if not ton_session:
            await callback.answer(
                "Кошелек не подключен. Используйте ручную оплату.",
                show_alert=True
            )
            return

        # Check if already participating
        participants = await crud.get_raffle_participants(session, raffle_id)
        if any(p.user_id == user.id for p in participants):
            await callback.answer("Вы уже участвуете в этом розыгрыше!", show_alert=True)
            return

    try:
        # Get entry fee
        entry_fee = raffle.entry_fee_amount
        amount_nano = int(entry_fee * 1_000_000_000)

        # Generate payment comment
        payment_comment = ton_service.generate_payment_comment(
            raffle_id=raffle_id,
            user_id=user.id
        )

        # Send transaction via TON Connect
        await callback.message.edit_text(
            f"⏳ <b>Отправка транзакции...</b>\n\n"
            f"Сейчас откроется ваш кошелек с готовой транзакцией.\n"
            f"Подтвердите оплату в кошельке.",
            parse_mode="HTML"
        )

        result = await ton_connect_service.send_transaction(
            user_id=user.id,
            destination=settings.TON_WALLET_ADDRESS,
            amount_nano=amount_nano,
            comment=payment_comment
        )

        await callback.message.edit_text(
            f"✅ <b>Транзакция отправлена!</b>\n\n"
            f"Сумма: {entry_fee:.4f} TON\n"
            f"Кошелек: <code>{ton_session.wallet_address[:8]}...{ton_session.wallet_address[-4:]}</code>\n\n"
            f"⏳ Ожидаем подтверждения в блокчейне...\n\n"
            f"Бот автоматически зарегистрирует ваше участие после подтверждения транзакции "
            f"(обычно занимает {settings.TON_TRANSACTION_CHECK_INTERVAL} секунд).",
            reply_markup=back_button(),
            parse_mode="HTML"
        )

        logger.info(
            f"TON Connect transaction sent for user {user.telegram_id}, "
            f"raffle {raffle_id}, amount: {entry_fee} TON"
        )

    except TonConnectError as e:
        logger.error(f"TON Connect payment failed: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка оплаты</b>\n\n"
            f"Не удалось отправить транзакцию через TON Connect.\n\n"
            f"Возможные причины:\n"
            f"• Вы отклонили транзакцию в кошельке\n"
            f"• Недостаточно средств\n"
            f"• Проблемы с подключением\n\n"
            f"Попробуйте еще раз или используйте ручную оплату.",
            reply_markup=back_button(),
            parse_mode="HTML"
        )

    await callback.answer()


@router.callback_query(F.data == "connect_and_pay_ton")
async def callback_connect_and_pay_ton(callback: CallbackQuery):
    """Connect TON wallet and then pay"""
    await callback.message.edit_text(
        f"🔗 <b>Подключение кошелька</b>\n\n"
        f"Для быстрой оплаты через TON Connect сначала подключите кошелек.\n\n"
        f"После подключения вы сможете оплачивать участие в один клик!\n\n"
        f"Нажмите кнопку ниже, чтобы начать подключение.",
        reply_markup=ton_connect_keyboard(is_connected=False),
        parse_mode="HTML"
    )
    await callback.answer()


@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    """Handle pre-checkout query for Stars payment"""
    # Always approve for now
    # In production, you might want to do additional validation
    await pre_checkout_query.answer(ok=True)
    logger.info(f"Pre-checkout approved for user {pre_checkout_query.from_user.id}")


@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    """Handle successful Stars payment"""
    payment_info = message.successful_payment
    logger.info(
        f"Successful payment from user {message.from_user.id}, "
        f"amount: {payment_info.total_amount}, "
        f"payload: {payment_info.invoice_payload}"
    )

    # Check if this is an admin payout
    if payment_info.invoice_payload.startswith("payout_"):
        await process_admin_payout_payment(message)
        return

    # Extract raffle_id from payload for regular raffle entry
    try:
        raffle_id = int(payment_info.invoice_payload.split("_")[1])
    except (IndexError, ValueError):
        logger.error(f"Invalid payload: {payment_info.invoice_payload}")
        await message.answer("Ошибка обработки платежа. Свяжитесь с поддержкой.")
        return

    async with get_session() as session:
        # Get or create user
        user = await crud.get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )

        # Create transaction
        transaction = await crud.create_transaction(
            session,
            user_id=user.id,
            type=TransactionType.RAFFLE_ENTRY,
            amount=settings.STARS_ENTRY_FEE,
            currency=CurrencyType.STARS,
            payment_id=payment_info.telegram_payment_charge_id,
            description=f"Участие в розыгрыше #{raffle_id}",
            payment_metadata={"raffle_id": raffle_id}
        )

        # Mark transaction as completed
        await crud.update_transaction_status(
            session, transaction.id, TransactionStatus.COMPLETED
        )

        # Add participant to raffle
        try:
            participant = await crud.add_participant(
                session,
                raffle_id=raffle_id,
                user_id=user.id,
                transaction_id=transaction.id,
            )

            # Get raffle info
            raffle = await crud.get_raffle_by_id(session, raffle_id)
            participants_count = len(await crud.get_raffle_participants(session, raffle_id))

            await message.answer(
                f"✅ <b>Оплата успешна!</b>\n\n"
                f"Вы успешно присоединились к розыгрышу #{raffle_id}\n"
                f"Ваш номер участника: {participant.participant_number}\n\n"
                f"Участников: {participants_count}/{raffle.min_participants}\n\n"
                f"Розыгрыш начнется автоматически при достижении минимального количества участников.",
                parse_mode="HTML"
            )

            logger.info(
                f"User {user.telegram_id} joined raffle {raffle_id}, "
                f"participant #{participant.participant_number}"
            )

        except ValueError as e:
            # Already participating - refund needed
            logger.warning(f"User {user.telegram_id} already in raffle {raffle_id}")
            await crud.update_transaction_status(
                session, transaction.id, TransactionStatus.FAILED
            )
            await message.answer(
                "Вы уже участвуете в этом розыгрыше. "
                "Средства будут возвращены автоматически."
            )


async def process_admin_payout_payment(message: Message):
    """
    Handle successful payment from admin for winner payout

    When admin pays the invoice:
    1. Stars are received by the bot
    2. Stars are credited to winner's balance in DB
    3. Winner can use balance for participating in raffles
    """
    payment_info = message.successful_payment

    # Parse payload: payout_{raffle_id}_{winner_id}
    try:
        parts = payment_info.invoice_payload.split("_")
        raffle_id = int(parts[1])
        winner_telegram_id = int(parts[2])
        amount = payment_info.total_amount

        logger.info(
            f"Processing admin payout: raffle={raffle_id}, "
            f"winner={winner_telegram_id}, amount={amount}"
        )

    except (IndexError, ValueError) as e:
        logger.error(f"Invalid payout payload: {payment_info.invoice_payload}")
        await message.answer(
            "❌ Ошибка обработки платежа.\n"
            "Неверный формат данных."
        )
        return

    async with get_session() as session:
        try:
            # Get payout request
            payout = await crud.get_payout_request_by_raffle(session, raffle_id)
            if not payout:
                logger.error(f"Payout request not found for raffle {raffle_id}")
                await message.answer(
                    "❌ Запрос на выплату не найден."
                )
                return

            # Get winner user
            winner = await crud.get_user_by_telegram_id(session, winner_telegram_id)
            if not winner:
                logger.error(f"Winner user {winner_telegram_id} not found")
                await message.answer(
                    "❌ Пользователь-победитель не найден в базе данных."
                )
                return

            # Get raffle info
            raffle = await crud.get_raffle_by_id(session, raffle_id)
            currency = raffle.entry_fee_type if raffle else CurrencyType.STARS

            # Credit Stars to winner's balance in DB
            await crud.update_user_balance(
                session,
                user_id=winner.id,
                amount=amount,
                currency=currency,
            )

            # Create transaction record
            await crud.create_transaction(
                session,
                user_id=winner.id,
                type=TransactionType.RAFFLE_WIN,
                amount=amount,
                currency=currency,
                payment_id=payment_info.telegram_payment_charge_id,
                description=f"Приз за победу в розыгрыше #{raffle_id}",
                payment_metadata={
                    "raffle_id": raffle_id,
                    "admin_id": message.from_user.id,
                    "telegram_charge_id": payment_info.telegram_payment_charge_id,
                }
            )

            # Update payout request status
            admin_user = await crud.get_user_by_telegram_id(session, message.from_user.id)
            await crud.update_payout_status(
                session,
                payout_id=payout.id,
                status=crud.PayoutStatus.COMPLETED,
                admin_id=admin_user.id if admin_user else None,
            )

            await session.commit()

            # Format currency display
            currency_symbol = "⭐" if currency == CurrencyType.STARS else "₽"
            amount_str = f"{int(amount)}" if currency == CurrencyType.STARS else f"{amount:.2f}"

            # Notify admin
            await message.answer(
                f"✅ <b>Выплата подтверждена!</b>\n\n"
                f"💫 {amount_str} {currency_symbol} зачислены на баланс победителя\n"
                f"🏆 Розыгрыш: #{raffle_id}\n"
                f"👤 Победитель: {winner.first_name}"
                f"{f' (@{winner.username})' if winner.username else ''}\n"
                f"📝 ID транзакции: {payment_info.telegram_payment_charge_id}\n\n"
                f"Победитель может использовать баланс для участия в новых розыгрышах!",
                parse_mode="HTML"
            )

            # Notify winner
            winner_message = (
                f"🎉 <b>Поздравляем с победой!</b>\n\n"
                f"Вам зачислено {amount_str} {currency_symbol} на баланс!\n"
                f"🏆 Приз за победу в розыгрыше #{raffle_id}\n\n"
                f"💰 Ваш баланс: {winner.balance_stars if currency == CurrencyType.STARS else winner.balance_rub} {currency_symbol}\n\n"
                f"Вы можете использовать баланс для участия в новых розыгрышах!\n"
                f"Используйте команду /balance для просмотра баланса."
            )

            await message.bot.send_message(
                winner_telegram_id,
                winner_message,
                parse_mode="HTML"
            )

            logger.info(
                f"Admin payout completed: raffle={raffle_id}, "
                f"winner={winner_telegram_id}, amount={amount}, "
                f"new_balance={winner.balance_stars if currency == CurrencyType.STARS else winner.balance_rub}"
            )

        except Exception as e:
            logger.error(f"Error processing admin payout: {e}", exc_info=True)
            await session.rollback()
            await message.answer(
                "❌ <b>Ошибка при обработке выплаты</b>\n\n"
                "Свяжитесь с технической поддержкой.\n"
                f"Код ошибки: {str(e)[:100]}",
                parse_mode="HTML"
            )
