from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.config import settings


def main_menu() -> InlineKeyboardMarkup:
    """Main menu keyboard"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="🎁 Участвовать в розыгрыше", callback_data="join_raffle")
    )
    builder.row(
        InlineKeyboardButton(text="💰 Мой баланс", callback_data="balance"),
        InlineKeyboardButton(text="💸 Вывод средств", callback_data="withdraw")
    )
    builder.row(
        InlineKeyboardButton(text="🎁 Текущий розыгрыш", callback_data="current_raffle"),
        InlineKeyboardButton(text="📜 История", callback_data="history")
    )
    builder.row(
        InlineKeyboardButton(text="❓ Помощь", callback_data="help"),
        InlineKeyboardButton(text="ℹ️ Правила", callback_data="rules")
    )

    return builder.as_markup()


def payment_choice(stars_fee: int = 0, rub_fee: int = 0, ton_fee: float = 0) -> InlineKeyboardMarkup:
    """Payment method selection keyboard"""
    builder = InlineKeyboardBuilder()

    # TON ONLY mode - show only TON payment
    if settings.TON_ONLY:
        builder.row(
            InlineKeyboardButton(
                text=f"💎 Оплатить TON ({ton_fee:.2f} TON)",
                callback_data="pay_ton"
            )
        )
    else:
        # Legacy mode: show Stars and RUB
        builder.row(
            InlineKeyboardButton(
                text=f"⭐ Оплатить звездами ({stars_fee} ⭐)",
                callback_data="pay_stars"
            )
        )

        # Show RUB payment button only if not in STARS_ONLY mode
        if not settings.STARS_ONLY:
            builder.row(
                InlineKeyboardButton(
                    text=f"💳 Оплатить рублями ({rub_fee} RUB)",
                    callback_data="pay_rub"
                )
            )

    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")
    )

    return builder.as_markup()


def admin_menu() -> InlineKeyboardMarkup:
    """Admin panel keyboard"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="Создать розыгрыш", callback_data="admin_create_raffle")
    )
    builder.row(
        InlineKeyboardButton(text="Текущий розыгрыш", callback_data="admin_current_raffle"),
        InlineKeyboardButton(text="Статистика", callback_data="admin_stats")
    )
    builder.row(
        InlineKeyboardButton(text="Остановить розыгрыш", callback_data="admin_stop_raffle"),
        InlineKeyboardButton(text="Запустить розыгрыш", callback_data="admin_start_raffle")
    )
    builder.row(
        InlineKeyboardButton(text="💸 Заявки на вывод", callback_data="admin_withdrawals")
    )
    builder.row(
        InlineKeyboardButton(text="Настройки", callback_data="admin_settings")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Выход", callback_data="back_to_menu")
    )

    return builder.as_markup()


def confirm_raffle_start() -> InlineKeyboardMarkup:
    """Confirmation keyboard for starting raffle"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="admin_confirm_start"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="admin_menu")
    )

    return builder.as_markup()


def back_button() -> InlineKeyboardMarkup:
    """Simple back button"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")
    )

    return builder.as_markup()


def raffle_info_keyboard(raffle_id: int) -> InlineKeyboardMarkup:
    """Keyboard for raffle information"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="Участвовать", callback_data=f"join_raffle_{raffle_id}")
    )
    builder.row(
        InlineKeyboardButton(text="Участники", callback_data=f"raffle_participants_{raffle_id}"),
        InlineKeyboardButton(text="Обновить", callback_data=f"raffle_refresh_{raffle_id}")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")
    )

    return builder.as_markup()


def verification_link_keyboard(verification_url: str) -> InlineKeyboardMarkup:
    """Keyboard with Random.org verification link"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🔍 Проверить на Random.org",
            url=verification_url
        )
    )
    builder.row(
        InlineKeyboardButton(text="◀️ В меню", callback_data="back_to_menu")
    )

    return builder.as_markup()


def balance_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for balance screen"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="💸 Вывести средства", callback_data="withdraw")
    )
    builder.row(
        InlineKeyboardButton(text="📜 История выводов", callback_data="my_withdrawals")
    )
    if settings.TON_ONLY:
        builder.row(
            InlineKeyboardButton(text="💎 Указать TON кошелек", callback_data="set_ton_wallet")
        )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")
    )

    return builder.as_markup()


def admin_withdrawal_keyboard(withdrawal_id: int) -> InlineKeyboardMarkup:
    """Keyboard for admin withdrawal approval"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Одобрить",
            callback_data=f"admin_approve_withdrawal_{withdrawal_id}"
        ),
        InlineKeyboardButton(
            text="❌ Отклонить",
            callback_data=f"admin_reject_withdrawal_{withdrawal_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin_withdrawals")
    )

    return builder.as_markup()


def ton_payment_keyboard(
    tonkeeper_url: str,
    ton_url: str,
    raffle_id: int
) -> InlineKeyboardMarkup:
    """
    Keyboard for TON payment with deep links

    Args:
        tonkeeper_url: Tonkeeper deep link
        ton_url: Generic TON wallet deep link
        raffle_id: Raffle ID for refresh callback

    Returns:
        InlineKeyboardMarkup with payment buttons
    """
    builder = InlineKeyboardBuilder()

    # Main payment button (Tonkeeper - most popular)
    builder.row(
        InlineKeyboardButton(
            text="💎 Открыть кошелек для оплаты",
            url=tonkeeper_url
        )
    )

    # Alternative wallet button
    builder.row(
        InlineKeyboardButton(
            text="🔗 Другой TON кошелек",
            url=ton_url
        )
    )

    # Refresh button to check payment status
    builder.row(
        InlineKeyboardButton(
            text="🔄 Проверить оплату",
            callback_data=f"check_ton_payment_{raffle_id}"
        )
    )

    # Manual payment option (fallback)
    builder.row(
        InlineKeyboardButton(
            text="📋 Показать данные для ручного ввода",
            callback_data=f"show_manual_ton_payment_{raffle_id}"
        )
    )

    # Cancel button
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_menu")
    )

    return builder.as_markup()
