import requests
import json
import base64
from typing import Dict, Any, Optional
from urllib.parse import quote
from loguru import logger

from app.config import settings


class RandomOrgError(Exception):
    """Random.org API error"""
    pass


class RandomOrgService:
    """Service for Random.org Signed API integration"""

    API_URL = "https://api.random.org/json-rpc/4/invoke"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.RANDOM_ORG_API_KEY

    def get_signed_random(self, min_val: int, max_val: int) -> Dict[str, Any]:
        """
        Get signed random integer from Random.org

        Args:
            min_val: Minimum value (inclusive)
            max_val: Maximum value (inclusive)

        Returns:
            Dictionary containing:
            - random_number: The random number
            - signature: Cryptographic signature
            - serial_number: Serial number for verification
            - full_response: Complete API response

        Raises:
            RandomOrgError: If API call fails
        """
        payload = {
            "jsonrpc": "2.0",
            "method": "generateSignedIntegers",
            "params": {
                "apiKey": self.api_key,
                "n": 1,
                "min": min_val,
                "max": max_val,
                "replacement": True,
            },
            "id": 1
        }

        try:
            logger.info(f"Requesting random number from Random.org (range: {min_val}-{max_val})")
            response = requests.post(
                self.API_URL,
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                error_msg = data["error"].get("message", "Unknown error")
                logger.error(f"Random.org API error: {error_msg}")
                raise RandomOrgError(f"Random.org API error: {error_msg}")

            result = data.get("result", {})
            random_data = result.get("random", {})
            random_number = random_data.get("data", [None])[0]

            if random_number is None:
                raise RandomOrgError("No random number in response")

            # Extract serial number from the correct location
            serial_number = random_data.get("serialNumber")

            logger.info(f"Received random number: {random_number}")
            logger.debug(f"Serial number: {serial_number}")

            return {
                "random_number": random_number,
                "signature": result.get("signature"),
                "serial_number": serial_number,
                "full_response": result,
            }

        except requests.RequestException as e:
            logger.error(f"Random.org request failed: {e}")
            raise RandomOrgError(f"Failed to connect to Random.org: {e}")

    def verify_signature(self, signed_data: Dict[str, Any]) -> bool:
        """
        Verify Random.org signature

        Note: Full verification requires additional crypto libraries.
        This is a placeholder for future implementation.

        Args:
            signed_data: The signed data from Random.org

        Returns:
            True if signature is valid (currently always True)
        """
        # TODO: Implement full signature verification
        # For now, we trust that the signature exists
        return "signature" in signed_data and signed_data["signature"] is not None

    def get_verification_url(self, full_response: Dict[str, Any]) -> str:
        """
        Get URL for public verification of the random number

        Args:
            full_response: Full response from Random.org containing random object and signature

        Returns:
            URL for verification page with encoded random data and signature
        """
        try:
            # Extract random object and signature from response
            random_object = full_response.get("random", {})
            signature = full_response.get("signature", "")

            # Convert random object to JSON string and base64 encode it
            random_json = json.dumps(random_object, separators=(',', ':'))
            random_base64 = base64.b64encode(random_json.encode('utf-8')).decode('utf-8')

            # URL encode the signature
            signature_encoded = quote(signature, safe='')

            # Construct verification URL
            verification_url = (
                f"https://api.random.org/signatures/form"
                f"?format=json"
                f"&random={random_base64}"
                f"&signature={signature_encoded}"
            )

            logger.debug(f"Generated verification URL with signature length: {len(signature)}")

            return verification_url

        except Exception as e:
            logger.error(f"Error generating verification URL: {e}")
            # Fallback to simple verification page
            return "https://api.random.org/signatures/form"


# Global service instance
random_service = RandomOrgService()
