import base64
import hashlib
import hmac
from typing import Dict, Union


class WebhookSignatureVerifier:
    """
    Cryptographic verification for incoming webhook requests.
    Validates HMAC-SHA256 signatures against the configured Auth Token.
    """

    @staticmethod
    def compute_signature(
        url: str,
        params: Dict[str, Union[str, int, float]],
        auth_token: str,
        nonce: str = "",
    ) -> str:
        """
        Computes the standard HMAC-SHA256 signature following provider specifications:
        1. Appends sorted key-value query/body parameters to the base URL.
        2. Appends the nonce if provided.
        3. Computes the HMAC-SHA256 hash using the secret auth token.
        4. Base64 encodes the resulting digest.
        """
        # Sort parameter keys alphabetically
        sorted_keys = sorted(params.keys())
        data_to_sign = url
        for key in sorted_keys:
            data_to_sign += f"{key}{params[key]}"
        if nonce:
            data_to_sign += nonce

        # Calculate HMAC-SHA256
        mac = hmac.new(
            key=auth_token.encode("utf-8"),
            msg=data_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        )
        return base64.b64encode(mac.digest()).decode("utf-8")

    @classmethod
    def verify_signature(
        cls,
        url: str,
        params: Dict[str, Union[str, int, float]],
        auth_token: str,
        signature: str,
        nonce: str = "",
    ) -> bool:
        """
        Verifies the request signature using constant-time comparison
        to protect against timing analysis attacks.
        """
        if not signature or not auth_token:
            return False

        expected_sig = cls.compute_signature(url, params, auth_token, nonce)
        return hmac.compare_digest(expected_sig, signature)
