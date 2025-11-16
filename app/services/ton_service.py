"""
TON Blockchain Service

This service handles:
- Monitoring incoming TON transactions
- Sending automated payouts to winners
- Wallet balance checking
- Transaction verification

Uses pytoniq library for TON blockchain interaction
"""

import asyncio
from typing import Optional, Dict, Any, List
from decimal import Decimal
from datetime import datetime, timedelta
import hashlib

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

        Connects to TON Center API and initializes wallet for payouts
        """
        self.api_key = settings.TON_CENTER_API_KEY
        self.wallet_address = settings.TON_WALLET_ADDRESS
        self.network = settings.TON_NETWORK
        self.is_testnet = self.network == "testnet"

        # Store last processed transaction timestamp
        self.last_transaction_lt = 0
        self.last_transaction_hash = ""

        # Initialize client lazily
        self._client = None
        self._wallet = None

        logger.info(
            f"TON service initialized for {self.network} "
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
        Get wallet balance in TON

        Returns:
            Balance in TON (float)

        Raises:
            TonPaymentError: If balance check fails
        """
        try:
            client = await self._get_client()
            address = Address(self.wallet_address)

            # Get account state
            account = await client.get_account_state(address)

            # Check if account is initialized
            if account is None:
                logger.warning(f"Account {self.wallet_address} is not initialized on blockchain")
                return 0.0

            # Convert from nanoTON to TON
            balance_nano = account.balance
            balance_ton = balance_nano / 1_000_000_000

            logger.debug(f"Wallet balance: {balance_ton:.4f} TON")
            return balance_ton

        except Exception as e:
            logger.error(f"Failed to get wallet balance: {e}")
            raise TonPaymentError(f"Failed to get balance: {e}")

    async def check_incoming_transactions(
        self,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Check for new incoming transactions

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
            client = await self._get_client()
            address = Address(self.wallet_address)

            # Check if account is initialized first
            account = await client.get_account_state(address)
            if account is None:
                logger.debug(f"Account {self.wallet_address} is not initialized, no transactions to check")
                return []

            # Get recent transactions
            transactions = await client.get_transactions(
                address=address,
                count=limit
            )

            # Handle None or empty transactions
            if not transactions:
                logger.debug("No transactions found")
                return []

            incoming_txs = []

            for tx in transactions:
                # Skip if already processed (check logical time)
                if tx.lt <= self.last_transaction_lt:
                    continue

                # Check if transaction has incoming message
                if not tx.in_msg:
                    continue

                in_msg = tx.in_msg

                # Skip if no value transferred
                if in_msg.info.value_coins == 0:
                    continue

                # Get sender address
                from_address = in_msg.info.src.to_str() if in_msg.info.src else None

                # Skip if no sender (internal transaction)
                if not from_address:
                    continue

                # Get amount in TON
                amount_nano = in_msg.info.value_coins
                amount_ton = amount_nano / 1_000_000_000

                # Extract comment from message body
                comment = ""
                try:
                    if in_msg.body:
                        # Try to parse comment (text message starts with 0x00000000)
                        cell = in_msg.body
                        slice_data = cell.begin_parse()

                        # Check if it's a text message (op = 0)
                        if slice_data.load_uint(32) == 0:
                            comment = slice_data.load_bytes(slice_data.remaining_bytes).decode('utf-8', errors='ignore')
                except Exception as e:
                    logger.debug(f"Could not parse comment: {e}")

                # Get transaction hash
                tx_hash = tx.cell.hash.hex()

                incoming_txs.append({
                    "hash": tx_hash,
                    "from_address": from_address,
                    "amount": amount_ton,
                    "comment": comment.strip(),
                    "timestamp": datetime.fromtimestamp(tx.now),
                    "lt": tx.lt,
                })

                logger.info(
                    f"Incoming TON transaction: {amount_ton:.4f} TON "
                    f"from {from_address[:8]}... "
                    f"comment: '{comment}'"
                )

            # Update last processed transaction
            if incoming_txs:
                self.last_transaction_lt = max(tx["lt"] for tx in incoming_txs)

            return incoming_txs

        except Exception as e:
            logger.error(f"Failed to check incoming transactions: {e}")
            raise TonPaymentError(f"Failed to check transactions: {e}")

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

    async def verify_transaction(
        self,
        tx_hash: str,
        expected_amount: Optional[float] = None,
        expected_sender: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify transaction details

        Args:
            tx_hash: Transaction hash to verify
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
            client = await self._get_client()
            address = Address(self.wallet_address)

            # Get recent transactions
            transactions = await client.get_transactions(address=address, count=100)

            # Find transaction by hash
            tx = None
            for t in transactions:
                if t.cell.hash.hex() == tx_hash:
                    tx = t
                    break

            if not tx:
                return {
                    "valid": False,
                    "error": "Transaction not found"
                }

            # Get transaction details
            in_msg = tx.in_msg
            if not in_msg:
                return {
                    "valid": False,
                    "error": "No incoming message"
                }

            amount_ton = in_msg.info.value_coins / 1_000_000_000
            sender = in_msg.info.src.to_str() if in_msg.info.src else None

            # Verify expected values
            valid = True
            if expected_amount and abs(amount_ton - expected_amount) > 0.001:
                valid = False

            if expected_sender and sender != expected_sender:
                valid = False

            return {
                "valid": valid,
                "amount": amount_ton,
                "sender": sender,
                "timestamp": datetime.fromtimestamp(tx.now),
                "confirmations": 1  # TON has near-instant finality
            }

        except Exception as e:
            logger.error(f"Failed to verify transaction: {e}")
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

    async def close(self):
        """Close TON client connection"""
        if self._client:
            await self._client.close_all()
            self._client = None
            self._wallet = None
            logger.info("TON client closed")


# Global service instance
ton_service = TonService()
