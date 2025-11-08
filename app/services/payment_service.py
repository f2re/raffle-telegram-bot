from typing import Optional, Dict, Any
from uuid import uuid4

from yookassa import Configuration, Payment, Payout
from loguru import logger

from app.config import settings


class PaymentError(Exception):
    """Payment processing error"""
    pass


class YooKassaService:
    """Service for YooKassa payment processing"""

    def __init__(self):
        if settings.YOOKASSA_SHOP_ID and settings.YOOKASSA_SECRET_KEY:
            Configuration.account_id = settings.YOOKASSA_SHOP_ID
            Configuration.secret_key = settings.YOOKASSA_SECRET_KEY
            self.enabled = True
            logger.info("YooKassa payment service initialized")
        else:
            self.enabled = False
            logger.warning("YooKassa credentials not provided, RUB payments disabled")

    def create_payment(
        self,
        amount: float,
        description: str,
        user_id: int,
        return_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create payment in YooKassa

        Args:
            amount: Amount in rubles
            description: Payment description
            user_id: User ID for metadata
            return_url: URL to redirect after payment

        Returns:
            Dictionary with payment_id and confirmation_url

        Raises:
            PaymentError: If payment creation fails
        """
        if not self.enabled:
            raise PaymentError("YooKassa payment service is not configured")

        try:
            idempotence_key = str(uuid4())

            payment = Payment.create({
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": return_url or "https://t.me/your_bot"
                },
                "capture": True,
                "description": description,
                "metadata": {
                    "user_id": str(user_id)
                }
            }, idempotence_key)

            logger.info(f"Payment created: {payment.id} for user {user_id}, amount: {amount} RUB")

            return {
                "payment_id": payment.id,
                "confirmation_url": payment.confirmation.confirmation_url,
                "status": payment.status,
            }

        except Exception as e:
            logger.error(f"Failed to create payment: {e}")
            raise PaymentError(f"Failed to create payment: {e}")

    def check_payment(self, payment_id: str) -> Dict[str, Any]:
        """
        Check payment status

        Args:
            payment_id: YooKassa payment ID

        Returns:
            Dictionary with payment status and details

        Raises:
            PaymentError: If check fails
        """
        if not self.enabled:
            raise PaymentError("YooKassa payment service is not configured")

        try:
            payment = Payment.find_one(payment_id)

            return {
                "payment_id": payment.id,
                "status": payment.status,
                "paid": payment.paid,
                "amount": float(payment.amount.value),
                "currency": payment.amount.currency,
                "metadata": payment.metadata,
            }

        except Exception as e:
            logger.error(f"Failed to check payment {payment_id}: {e}")
            raise PaymentError(f"Failed to check payment: {e}")

    def create_payout(
        self,
        amount: float,
        card_number: Optional[str] = None,
        phone_number: Optional[str] = None,
        description: str = "Выплата приза",
    ) -> Dict[str, Any]:
        """
        Create payout to bank card or phone (SBP)

        Args:
            amount: Amount in rubles
            card_number: Bank card number (if paying to card)
            phone_number: Phone number (if paying via SBP)
            description: Payout description

        Returns:
            Dictionary with payout_id and status

        Raises:
            PaymentError: If payout creation fails
        """
        if not self.enabled:
            raise PaymentError("YooKassa payment service is not configured")

        if not card_number and not phone_number:
            raise PaymentError("Either card_number or phone_number must be provided")

        try:
            idempotence_key = str(uuid4())

            # Prepare payout destination
            if card_number:
                payout_destination = {
                    "type": "bank_card",
                    "card": {
                        "number": card_number
                    }
                }
            else:
                payout_destination = {
                    "type": "sbp",
                    "phone": phone_number
                }

            payout = Payout.create({
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": "RUB"
                },
                "payout_destination_data": payout_destination,
                "description": description,
            }, idempotence_key)

            logger.info(f"Payout created: {payout.id}, amount: {amount} RUB")

            return {
                "payout_id": payout.id,
                "status": payout.status,
                "amount": float(payout.amount.value),
            }

        except Exception as e:
            logger.error(f"Failed to create payout: {e}")
            raise PaymentError(f"Failed to create payout: {e}")

    def check_payout(self, payout_id: str) -> Dict[str, Any]:
        """
        Check payout status

        Args:
            payout_id: YooKassa payout ID

        Returns:
            Dictionary with payout status

        Raises:
            PaymentError: If check fails
        """
        if not self.enabled:
            raise PaymentError("YooKassa payment service is not configured")

        try:
            payout = Payout.find_one(payout_id)

            return {
                "payout_id": payout.id,
                "status": payout.status,
                "amount": float(payout.amount.value),
            }

        except Exception as e:
            logger.error(f"Failed to check payout {payout_id}: {e}")
            raise PaymentError(f"Failed to check payout: {e}")


# Global service instance
yookassa_service = YooKassaService()
