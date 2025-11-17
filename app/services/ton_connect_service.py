"""
TON Connect Service

This service handles TON Connect wallet connections:
- Managing wallet connections/disconnections
- Storing session data in Redis
- Initiating transactions via connected wallets
- Restoring wallet sessions

Uses pytonconnect library for TON Connect 2.0 protocol
"""

import asyncio
import json
from typing import Optional, Dict, Any
from datetime import datetime
from base64 import urlsafe_b64encode

from pytonconnect import TonConnect
from pytonconnect.storage import IStorage
from pytoniq_core import begin_cell
from loguru import logger
import redis.asyncio as aioredis

from app.config import settings
from app.database.session import get_session
from app.database import crud


class RedisStorage(IStorage):
    """
    Redis storage implementation for TON Connect sessions

    Stores session data in Redis for persistence and fast access
    """

    def __init__(self, redis_client: aioredis.Redis, key_prefix: str = "tonconnect:"):
        self.redis = redis_client
        self.key_prefix = key_prefix

    async def set_item(self, key: str, value: str):
        """Store item in Redis"""
        redis_key = f"{self.key_prefix}{key}"
        await self.redis.set(redis_key, value)

    async def get_item(self, key: str, default_value: Optional[str] = None) -> Optional[str]:
        """Get item from Redis"""
        redis_key = f"{self.key_prefix}{key}"
        value = await self.redis.get(redis_key)
        if value is None:
            return default_value
        return value.decode('utf-8') if isinstance(value, bytes) else value

    async def remove_item(self, key: str):
        """Remove item from Redis"""
        redis_key = f"{self.key_prefix}{key}"
        await self.redis.delete(redis_key)


class TonConnectError(Exception):
    """TON Connect operation error"""
    pass


class TonConnectService:
    """Service for managing TON Connect wallet connections"""

    def __init__(self):
        """
        Initialize TON Connect service

        Creates Redis connection pool and sets up manifest URL
        """
        self.manifest_url = settings.TON_CONNECT_MANIFEST_URL
        self.redis_url = settings.REDIS_URL
        self._redis_pool = None

        logger.info(f"TON Connect service initialized (manifest: {self.manifest_url})")

    async def _get_redis(self) -> aioredis.Redis:
        """Get or create Redis connection pool"""
        if self._redis_pool is None:
            self._redis_pool = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False
            )
        return self._redis_pool

    async def create_connector(self, user_id: int) -> TonConnect:
        """
        Create TON Connect instance for user

        Args:
            user_id: User ID (from database, NOT telegram_id)

        Returns:
            TonConnect instance with Redis storage
        """
        redis = await self._get_redis()
        storage = RedisStorage(redis, key_prefix=f"tonconnect:user:{user_id}:")

        connector = TonConnect(
            manifest_url=self.manifest_url,
            storage=storage
        )

        return connector

    async def get_connection_url(
        self,
        user_id: int,
        wallet_name: str = "tonkeeper"
    ) -> Dict[str, str]:
        """
        Generate TON Connect connection URL for wallet

        Args:
            user_id: User ID (from database)
            wallet_name: Wallet name (tonkeeper, tonhub, etc.)

        Returns:
            Dictionary with:
            - universal_url: Universal link for any wallet
            - qr_url: URL for QR code generation
            - deep_link: Deep link for specific wallet

        Raises:
            TonConnectError: If connection URL generation fails
        """
        try:
            connector = await self.create_connector(user_id)

            # Get available wallets (synchronous method)
            wallets = connector.get_wallets()

            # Find requested wallet or use first available
            wallet = None
            for w in wallets:
                if wallet_name.lower() in w['name'].lower():
                    wallet = w
                    break

            if not wallet and wallets:
                wallet = wallets[0]  # Fallback to first wallet

            if not wallet:
                raise TonConnectError("No wallets available")

            # Generate connection URL
            connection_url = await connector.connect(wallet)

            logger.info(
                f"Generated TON Connect URL for user {user_id}, "
                f"wallet: {wallet['name']}"
            )

            return {
                "universal_url": connection_url,
                "qr_url": connection_url,  # Can be used for QR code
                "deep_link": connection_url,
                "wallet_name": wallet['name'],
            }

        except Exception as e:
            logger.error(f"Failed to generate connection URL: {e}")
            raise TonConnectError(f"Failed to generate connection URL: {e}")

    async def check_connection(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Check if wallet is connected and return wallet info

        Args:
            user_id: User ID (from database)

        Returns:
            Wallet info if connected, None otherwise
            Contains: address, chain, publicKey, walletStateInit
        """
        try:
            connector = await self.create_connector(user_id)

            # Restore connection if exists
            is_connected = await connector.restore_connection()

            if not is_connected:
                return None

            # Get wallet info
            wallet = connector.wallet
            if not wallet:
                return None

            wallet_info = {
                "address": wallet.account.address,
                "chain": wallet.account.chain,
                "public_key": wallet.account.public_key if hasattr(wallet.account, 'public_key') else None,
                "wallet_state_init": wallet.account.wallet_state_init if hasattr(wallet.account, 'wallet_state_init') else None,
            }

            logger.debug(f"Wallet connected for user {user_id}: {wallet_info['address'][:8]}...")
            return wallet_info

        except Exception as e:
            logger.error(f"Failed to check connection for user {user_id}: {e}")
            return None

    async def disconnect_wallet(self, user_id: int) -> bool:
        """
        Disconnect wallet for user

        Args:
            user_id: User ID (from database)

        Returns:
            True if disconnected successfully
        """
        try:
            connector = await self.create_connector(user_id)

            # Disconnect wallet
            await connector.disconnect()

            # Update database
            async with get_session() as session:
                await crud.disconnect_ton_connect_session(session, user_id)
                await session.commit()

            logger.info(f"Wallet disconnected for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to disconnect wallet for user {user_id}: {e}")
            return False

    async def send_transaction(
        self,
        user_id: int,
        destination: str,
        amount_nano: int,
        comment: str = ""
    ) -> Dict[str, Any]:
        """
        Send transaction via TON Connect

        Args:
            user_id: User ID (from database)
            destination: Recipient TON address
            amount_nano: Amount in nanoTON (1 TON = 1_000_000_000 nanoTON)
            comment: Optional transaction comment

        Returns:
            Transaction result with boc (bag of cells)

        Raises:
            TonConnectError: If transaction fails
        """
        try:
            connector = await self.create_connector(user_id)

            # Check if wallet is connected
            is_connected = await connector.restore_connection()
            if not is_connected:
                raise TonConnectError("Wallet not connected")

            # Prepare transaction body (comment)
            payload = None
            if comment:
                # Text message format: 32-bit zero + UTF-8 text
                # Payload must be base64-encoded BOC
                body = (
                    begin_cell()
                    .store_uint(0, 32)  # Text message op code
                    .store_string(comment)  # Store comment as string
                    .end_cell()
                )

                # Encode to base64 (required by TON Connect)
                payload = urlsafe_b64encode(body.to_boc()).decode()

            # Create transaction
            transaction = {
                "valid_until": int(datetime.utcnow().timestamp()) + 300,  # Valid for 5 minutes
                "messages": [
                    {
                        "address": destination,
                        "amount": str(amount_nano),
                        "payload": payload,
                    }
                ]
            }

            # Send transaction
            result = await connector.send_transaction(transaction)

            logger.info(
                f"Transaction sent via TON Connect for user {user_id}: "
                f"{amount_nano / 1_000_000_000:.4f} TON to {destination[:8]}..."
            )

            return result

        except Exception as e:
            logger.error(f"Failed to send transaction for user {user_id}: {e}")
            raise TonConnectError(f"Transaction failed: {e}")

    async def listen_for_connection(
        self,
        user_id: int,
        timeout: int = 300
    ) -> Optional[Dict[str, Any]]:
        """
        Listen for wallet connection (polling)

        Args:
            user_id: User ID (from database)
            timeout: Timeout in seconds (default: 5 minutes)

        Returns:
            Wallet info when connected, None if timeout
        """
        try:
            connector = await self.create_connector(user_id)

            start_time = datetime.utcnow()
            check_interval = 2  # Check every 2 seconds

            while (datetime.utcnow() - start_time).total_seconds() < timeout:
                # Check connection status
                is_connected = await connector.restore_connection()

                if is_connected and connector.wallet:
                    wallet = connector.wallet
                    wallet_info = {
                        "address": wallet.account.address,
                        "chain": wallet.account.chain,
                        "public_key": wallet.account.public_key if hasattr(wallet.account, 'public_key') else None,
                        "wallet_state_init": wallet.account.wallet_state_init if hasattr(wallet.account, 'wallet_state_init') else None,
                    }

                    # Save to database
                    async with get_session() as session:
                        await crud.create_ton_connect_session(
                            session,
                            user_id=user_id,
                            wallet_address=wallet_info["address"],
                            wallet_public_key=wallet_info.get("public_key"),
                            wallet_state_init=wallet_info.get("wallet_state_init"),
                            session_data={"connected_at": datetime.utcnow().isoformat()}
                        )
                        await session.commit()

                    logger.info(
                        f"Wallet connected for user {user_id}: "
                        f"{wallet_info['address'][:8]}..."
                    )

                    return wallet_info

                # Wait before next check
                await asyncio.sleep(check_interval)

            logger.warning(f"Connection timeout for user {user_id}")
            return None

        except Exception as e:
            logger.error(f"Error listening for connection: {e}")
            return None

    async def close(self):
        """Close Redis connection"""
        if self._redis_pool:
            await self._redis_pool.close()
            logger.info("TON Connect service closed")


# Global service instance
ton_connect_service = TonConnectService()
