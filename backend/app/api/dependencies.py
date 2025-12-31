import hashlib
import hmac
from urllib.parse import parse_qs, unquote
from fastapi import HTTPException, Header
from typing import Dict, Any
import json

from backend.app.config import settings


def verify_telegram_data(init_data: str) -> Dict[str, Any]:
    """
    Verify Telegram WebApp init data using HMAC-SHA256
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    try:
        # Parse init data
        parsed = parse_qs(init_data)

        # Get hash from data
        received_hash = parsed.get('hash', [''])[0]
        if not received_hash:
            raise ValueError("No hash in init data")

        # Create data-check-string
        data_check_arr = []
        for key in sorted(parsed.keys()):
            if key != 'hash':
                value = parsed[key][0]
                data_check_arr.append(f"{key}={value}")
        data_check_string = '\n'.join(data_check_arr)

        # Calculate secret key
        secret_key = hmac.new(
            "WebAppData".encode(),
            settings.TELEGRAM_BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()

        # Calculate hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        # Verify hash
        if calculated_hash != received_hash:
            raise ValueError("Invalid hash")

        # Parse user data
        user_data = {}
        if 'user' in parsed:
            user_json = unquote(parsed['user'][0])
            user_data = json.loads(user_json)

        return {
            'user_id': user_data.get('id'),
            'username': user_data.get('username'),
            'first_name': user_data.get('first_name'),
            'last_name': user_data.get('last_name'),
            'language_code': user_data.get('language_code'),
            'is_premium': user_data.get('is_premium', False),
        }

    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid Telegram data: {str(e)}"
        )


async def get_current_user(authorization: str = Header(...)):
    """
    Extract and verify current user from Authorization header
    Header format: "tma <init_data>"
    """
    if not authorization.startswith("tma "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format"
        )

    init_data = authorization[4:]  # Remove "tma " prefix
    user_data = verify_telegram_data(init_data)

    if not user_data.get('user_id'):
        raise HTTPException(
            status_code=401,
            detail="No user ID in Telegram data"
        )

    return user_data
