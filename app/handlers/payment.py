from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice
from loguru import logger

from app.database.session import get_session
from app.database import crud
from app.database.models import CurrencyType, TransactionType, TransactionStatus
from app.config import settings
from app.services.payment_service import yookassa_service, PaymentError
from app.keyboards.inline import back_button

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
            metadata={"raffle_id": raffle.id}
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

    # Extract raffle_id from payload
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
            status=TransactionStatus.COMPLETED,
            metadata={"raffle_id": raffle_id}
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
