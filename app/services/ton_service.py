"""
TON Blockchain Service

This service handles:
- Monitoring incoming TON transactions
- Sending automated payouts to winners
- Wallet balance checking
- Transaction verification

Uses TON Console API (tonapi.io / tonconsole.com) for read operations
and pytoniq library for wallet operations (sending TON)
"""

import asyncio
from typing import Optional, Dict, Any, List
from decimal import Decimal
from datetime import datetime, timedelta
import hashlib

from pytonapi import AsyncTonapi
from pytoniq import LiteBalancer, WalletV4R2, begin_cell
from pytoniq_core import Address
from loguru import logger

from app.config import settings


class TonPaymentError(Exception):
    """TON payment processing error"""
    pass


class TonService:
    """Service for TON blockchain operations"""

    def __init__(self):
        """
        Initialize TON service

        Uses TON Console API (https://tonconsole.com) for read operations:
        - Get account balance
        - Monitor incoming transactions

        Uses pytoniq for wallet operations:
        - Send TON transactions (payouts, refunds)
        """
        self.api_key = settings.TON_CENTER_API_KEY  # Actually TON Console API key from https://tonconsole.com
        self.wallet_address = settings.TON_WALLET_ADDRESS
        self.network = settings.TON_NETWORK
        self.is_testnet = self.network == "testnet"

        # Store last processed transaction timestamp
        self.last_transaction_lt = 0
        self.last_transaction_hash = ""

        # Initialize TON Console API client
        self._tonapi = AsyncTonapi(
            api_key=self.api_key,
            is_testnet=self.is_testnet
        )

        # Initialize pytoniq client and wallet lazily (for sending transactions)
        self._client = None
        self._wallet = None

        logger.info(
            f"TON service initialized for {self.network} using TON Console API "
            f"(wallet: {self.wallet_address[:8]}...)"
        )

    async def _get_client(self):
        """Get or create LiteBalancer client"""
        if self._client is None:
            self._client = LiteBalancer.from_mainnet_config(
                trust_level=2,
                timeout=30
            ) if not self.is_testnet else LiteBalancer.from_testnet_config(
                trust_level=2,
                timeout=30
            )
            await self._client.start_up()
        return self._client

    async def _get_wallet(self):
        """Get or create wallet for sending transactions"""
        if self._wallet is None:
            client = await self._get_client()

            # Parse mnemonic
            mnemonic = settings.TON_WALLET_MNEMONIC.split()
            if len(mnemonic) != 24:
                raise TonPaymentError(
                    f"Invalid mnemonic: expected 24 words, got {len(mnemonic)}"
                )

            # Create wallet from mnemonic
            self._wallet = await WalletV4R2.from_mnemonic(
                client=client,
                mnemonics=mnemonic
            )

            logger.info(f"Wallet initialized: {self._wallet.address.to_str()}")

        return self._wallet

    async def get_balance(self) -> float:
        """
        Get wallet balance in TON using TON Console API

        Returns:
            Balance in TON (float)

        Raises:
            TonPaymentError: If balance check fails
        """
        try:
            # Get account info from TON Console API
            account = await self._tonapi.accounts.get_info(account_id=self.wallet_address)

            # Get balance in TON (pytonapi returns balance in amount format)
            balance_ton = float(account.balance.to_amount())

            logger.debug(f"Wallet balance: {balance_ton:.4f} TON (via TON Console API)")
            return balance_ton

        except Exception as e:
            logger.error(f"Failed to get wallet balance from TON Console API: {e}")
            raise TonPaymentError(f"Failed to get balance: {e}")

    async def check_incoming_transactions(
        self,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Check for new incoming transactions using TON Console API

        Args:
            limit: Maximum number of transactions to fetch

        Returns:
            List of transaction dictionaries with:
            - hash: Transaction hash
            - from_address: Sender address
            - amount: Amount in TON
            - comment: Transaction comment/memo
            - timestamp: Transaction timestamp
            - lt: Logical time

        Raises:
            TonPaymentError: If transaction check fails
        """
        try:
            # Get account events (transactions) from TON Console API
            events = await self._tonapi.accounts.get_events(
                account_id=self.wallet_address,
                limit=limit
            )

            incoming_txs = []

            for event in events.events:
                # Get the first action (usually the main transaction)
                if not event.actions:
                    continue

                for action in event.actions:
                    # We're interested in TonTransfer actions (incoming TON)
                    if action.type != "TonTransfer":
                        continue

                    ton_transfer = action.ton_transfer
                    if not ton_transfer:
                        continue

                    # Check if this is an incoming transaction (recipient is our wallet)
                    recipient_address = ton_transfer.recipient.address if ton_transfer.recipient else None
                    if not recipient_address or recipient_address.lower() != self.wallet_address.lower():
                        continue

                    # Get sender address
                    from_address = ton_transfer.sender.address if ton_transfer.sender else None
                    if not from_address:
                        continue

                    # Get amount in TON
                    amount_ton = float(ton_transfer.amount) / 1_000_000_000

                    # Skip zero-amount transactions
                    if amount_ton == 0:
                        continue

                    # Get comment from the transaction
                    comment = ton_transfer.comment if hasattr(ton_transfer, 'comment') and ton_transfer.comment else ""

                    # Get transaction hash and logical time
                    tx_hash = event.event_id
                    lt = event.lt

                    # Skip if already processed
                    if lt <= self.last_transaction_lt:
                        continue

                    # Get timestamp
                    timestamp = datetime.fromtimestamp(event.timestamp)

                    incoming_txs.append({
                        "hash": tx_hash,
                        "from_address": from_address,
                        "amount": amount_ton,
                        "comment": comment.strip(),
                        "timestamp": timestamp,
                        "lt": lt,
                    })

                    logger.info(
                        f"Incoming TON transaction: {amount_ton:.4f} TON "
                        f"from {from_address[:8]}... "
                        f"comment: '{comment}' (via TON Console API)"
                    )

            # Update last processed transaction
            if incoming_txs:
                self.last_transaction_lt = max(tx["lt"] for tx in incoming_txs)

            return incoming_txs

        except Exception as e:
            logger.error(f"Failed to check incoming transactions from TON Console API: {e}")
            # Return empty list instead of raising error (temporary network issues)
            logger.warning("Returning empty transaction list due to API error")
            return []

    async def send_ton(
        self,
        destination_address: str,
        amount_ton: float,
        comment: str = ""
    ) -> str:
        """
        Send TON to address

        Args:
            destination_address: Recipient's TON wallet address
            amount_ton: Amount in TON to send
            comment: Optional comment/memo

        Returns:
            Transaction hash

        Raises:
            TonPaymentError: If sending fails
        """
        try:
            wallet = await self._get_wallet()

            # Convert TON to nanoTON
            amount_nano = int(amount_ton * 1_000_000_000)

            # Parse destination address
            dest_address = Address(destination_address)

            # Create message body with comment
            body = None
            if comment:
                # Text message format: 32-bit zero + UTF-8 text
                body = (
                    begin_cell()
                    .store_uint(0, 32)  # Text message op code
                    .store_bytes(comment.encode('utf-8'))
                    .end_cell()
                )

            # Send transaction
            await wallet.transfer(
                destination=dest_address,
                amount=amount_nano,
                body=body
            )

            # Note: pytoniq doesn't directly return tx hash after send
            # We'll need to check recent transactions to get the hash
            # For now, return a placeholder
            tx_hash = hashlib.sha256(
                f"{destination_address}:{amount_ton}:{comment}:{datetime.utcnow()}".encode()
            ).hexdigest()

            logger.info(
                f"Sent {amount_ton:.4f} TON to {destination_address[:8]}... "
                f"comment: '{comment}'"
            )

            return tx_hash

        except Exception as e:
            logger.error(f"Failed to send TON: {e}")
            raise TonPaymentError(f"Failed to send TON: {e}")

    async def send_prize_payout(
        self,
        winner_address: str,
        amount_ton: float,
        raffle_id: int
    ) -> str:
        """
        Send prize payout to winner

        Args:
            winner_address: Winner's TON wallet address
            amount_ton: Prize amount in TON
            raffle_id: Raffle ID for comment

        Returns:
            Transaction hash

        Raises:
            TonPaymentError: If payout fails
        """
        comment = f"Raffle #{raffle_id} prize - Congratulations! 🎉"

        return await self.send_ton(
            destination_address=winner_address,
            amount_ton=amount_ton,
            comment=comment
        )

    async def send_refund(
        self,
        recipient_address: str,
        amount_ton: float,
        reason: str,
        raffle_id: int = None
    ) -> str:
        """
        Send refund to user

        Args:
            recipient_address: User's TON wallet address
            amount_ton: Refund amount in TON
            reason: Refund reason (e.g., "wrong amount", "already participating")
            raffle_id: Optional raffle ID

        Returns:
            Transaction hash

        Raises:
            TonPaymentError: If refund fails
        """
        raffle_info = f" (Raffle #{raffle_id})" if raffle_id else ""
        comment = f"Refund{raffle_info}: {reason}"

        logger.info(
            f"Sending refund: {amount_ton:.4f} TON to {recipient_address[:8]}... "
            f"Reason: {reason}"
        )

        return await self.send_ton(
            destination_address=recipient_address,
            amount_ton=amount_ton,
            comment=comment
        )

    async def check_balance_sufficient(self, required_amount: float) -> bool:
        """
        Check if wallet has sufficient balance for operation

        Args:
            required_amount: Required amount in TON

        Returns:
            True if balance is sufficient, False otherwise
        """
        try:
            current_balance = await self.get_balance()

            # Add 0.05 TON buffer for transaction fees
            required_with_fees = required_amount + 0.05

            if current_balance < required_with_fees:
                logger.warning(
                    f"Insufficient balance: have {current_balance:.4f} TON, "
                    f"need {required_with_fees:.4f} TON (including fees)"
                )
                return False

            return True
        except Exception as e:
            logger.error(f"Error checking balance: {e}")
            return False

    async def verify_transaction(
        self,
        tx_hash: str,
        expected_amount: Optional[float] = None,
        expected_sender: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify transaction details using TON Console API

        Args:
            tx_hash: Transaction event ID to verify
            expected_amount: Expected amount in TON (optional)
            expected_sender: Expected sender address (optional)

        Returns:
            Dictionary with verification results:
            - valid: Whether transaction is valid
            - amount: Actual amount
            - sender: Actual sender
            - confirmations: Number of confirmations

        Raises:
            TonPaymentError: If verification fails
        """
        try:
            # Get recent events to find the transaction
            events = await self._tonapi.accounts.get_events(
                account_id=self.wallet_address,
                limit=100
            )

            # Find transaction by event_id
            tx_event = None
            for event in events.events:
                if event.event_id == tx_hash:
                    tx_event = event
                    break

            if not tx_event:
                return {
                    "valid": False,
                    "error": "Transaction not found"
                }

            # Find the TonTransfer action
            amount_ton = 0.0
            sender = None

            for action in tx_event.actions:
                if action.type == "TonTransfer" and action.ton_transfer:
                    ton_transfer = action.ton_transfer

                    # Check if recipient is our wallet
                    recipient_address = ton_transfer.recipient.address if ton_transfer.recipient else None
                    if recipient_address and recipient_address.lower() == self.wallet_address.lower():
                        amount_ton = float(ton_transfer.amount) / 1_000_000_000
                        sender = ton_transfer.sender.address if ton_transfer.sender else None
                        break

            if not sender:
                return {
                    "valid": False,
                    "error": "No incoming transfer found"
                }

            # Verify expected values
            valid = True
            if expected_amount and abs(amount_ton - expected_amount) > 0.001:
                valid = False

            if expected_sender and sender.lower() != expected_sender.lower():
                valid = False

            return {
                "valid": valid,
                "amount": amount_ton,
                "sender": sender,
                "timestamp": datetime.fromtimestamp(tx_event.timestamp),
                "confirmations": 1  # TON has near-instant finality
            }

        except Exception as e:
            logger.error(f"Failed to verify transaction via TON Console API: {e}")
            raise TonPaymentError(f"Failed to verify transaction: {e}")

    def generate_payment_comment(self, raffle_id: int, user_id: int) -> str:
        """
        Generate unique payment comment for raffle entry

        Args:
            raffle_id: Raffle ID
            user_id: User ID

        Returns:
            Unique payment comment
        """
        return f"raffle_{raffle_id}_user_{user_id}"

    def parse_payment_comment(self, comment: str) -> Optional[Dict[str, int]]:
        """
        Parse payment comment to extract raffle_id and user_id

        Args:
            comment: Payment comment

        Returns:
            Dictionary with raffle_id and user_id, or None if invalid
        """
        try:
            parts = comment.strip().split("_")
            if len(parts) == 4 and parts[0] == "raffle" and parts[2] == "user":
                return {
                    "raffle_id": int(parts[1]),
                    "user_id": int(parts[3])
                }
        except (ValueError, IndexError):
            pass

        return None

    def generate_payment_deep_link(
        self,
        amount_ton: float,
        comment: str
    ) -> Dict[str, str]:
        """
        Generate TON payment deep links for different wallets

        Creates deep links that open TON wallets with pre-filled payment data.
        Supports Tonkeeper, TON Wallet, and Telegram Wallet (@wallet).

        Args:
            amount_ton: Amount in TON to send
            comment: Payment comment/memo

        Returns:
            Dictionary with deep links for different wallets:
            - tonkeeper: Tonkeeper app link
            - ton: Generic TON protocol link (works with Telegram Wallet and others)
            - universal: Universal link for all TON wallets
        """
        # Convert TON to nanoTON
        amount_nano = int(amount_ton * 1_000_000_000)

        # URL-encode the comment
        from urllib.parse import quote

        encoded_comment = quote(comment)

        # Generate links for different wallets
        links = {
            # Tonkeeper (most popular)
            "tonkeeper": (
                f"https://app.tonkeeper.com/transfer/{self.wallet_address}"
                f"?amount={amount_nano}&text={encoded_comment}"
            ),

            # Generic TON protocol link (works with Telegram Wallet, TON Wallet, and most wallets)
            # This is the standard TON deep link format
            "ton": (
                f"ton://transfer/{self.wallet_address}"
                f"?amount={amount_nano}&text={encoded_comment}"
            ),

            # Universal link (alternative format for compatibility)
            "universal": (
                f"https://ton.org/transfer/{self.wallet_address}"
                f"?amount={amount_nano}&text={encoded_comment}"
            ),
        }

        logger.debug(
            f"Generated payment deep links: amount={amount_ton} TON, "
            f"comment='{comment}'"
        )

        return links

    async def close(self):
        """Close TON client and API connections"""
        # Close TON Console API client
        if self._tonapi:
            await self._tonapi.close()
            logger.info("TON Console API client closed")

        # Close pytoniq client (for sending transactions)
        if self._client:
            await self._client.close_all()
            self._client = None
            self._wallet = None
            logger.info("TON pytoniq client closed")


# Global service instance
ton_service = TonService()
