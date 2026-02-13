from __future__ import annotations

import base64
import os
from typing import Optional

# RootKeyProvider comes from the SES‑Core package, not a top‑level module.
from ses_core import RootKeyProvider  # type: ignore[import]


def _lazy_boto3():
    """
    Load boto3 only when we actually need to talk to AWS.
    This keeps local/dev runs from breaking if boto3 is not installed.
    """
    try:
        import boto3  # type: ignore
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise RuntimeError(
            "AwsSecretsRootKeyProvider requires the 'boto3' package. "
            "Install it in your AWS environment (e.g. 'pip install boto3')."
        ) from exc
    return boto3


class AwsSecretsRootKeyProvider(RootKeyProvider):
    """
    SES‑Core RootKeyProvider that loads the root key from AWS Secrets Manager.

    Expected configuration (environment variables):

      * TFE_SES_ROOT_SECRET_ID  – name or ARN of the secret that holds the root key
      * AWS_REGION              – AWS region for Secrets Manager (e.g. 'us-east-1')

    The secret value may be:
      * hex string (preferred); or
      * base64 string; or
      * raw UTF‑8 string of at least 32 bytes.
    """

    def __init__(
        self,
        secret_id: Optional[str] = None,
        region_name: Optional[str] = None,
        cache: bool = True,
    ) -> None:
        self._secret_id = secret_id or os.environ.get("TFE_SES_ROOT_SECRET_ID", "")
        self._region_name = region_name or os.environ.get("AWS_REGION", "")
        self._cache_enabled = cache
        self._cached_key: Optional[bytes] = None

    # ------------------------
    # Helpers
    # ------------------------
    def _load_secret_string(self) -> str:
        boto3 = _lazy_boto3()

        if not self._secret_id:
            raise RuntimeError(
                "AwsSecretsRootKeyProvider: no secret id provided. "
                "Set TFE_SES_ROOT_SECRET_ID or pass secret_id=..."
            )

        # Region is optional; if empty, boto3 will fall back to its default chain.
        client = boto3.client(
            "secretsmanager",
            region_name=self._region_name or None,
        )
        response = client.get_secret_value(SecretId=self._secret_id)

        if "SecretString" in response:
            return str(response["SecretString"])

        # Binary secret -> base64 decode to text, then treat as key text
        binary = response.get("SecretBinary")
        if binary is None:
            raise RuntimeError("AwsSecretsRootKeyProvider: empty secret value")

        return base64.b64decode(binary).decode("utf-8")

    @staticmethod
    def _parse_secret_bytes(value: str) -> bytes:
        """
        Turn the secret string into key bytes.

        Accepts:
          * hex
          * base64
          * raw utf‑8 (length >= 32)
        """
        text = value.strip()

        # Try hex
        try:
            b = bytes.fromhex(text)
            if len(b) >= 32:
                return b
        except ValueError:
            pass

        # Try base64
        try:
            b = base64.b64decode(text)
            if len(b) >= 32:
                return b
        except Exception:
            pass

        # Fallback: raw utf‑8
        b = text.encode("utf-8")
        if len(b) < 32:
            raise ValueError(
                "AWS root key secret must be at least 32 bytes "
                "(after decoding)."
            )
        return b

    # ------------------------
    # RootKeyProvider interface
    # ------------------------
    def get_root_key(self) -> bytes:  # type: ignore[override]
        """
        Return the root key bytes for SES‑Core HKDF.

        This is cached in‑process if cache=True.
        """
        if self._cache_enabled and self._cached_key is not None:
            return self._cached_key

        secret_text = self._load_secret_string()
        key_bytes = self._parse_secret_bytes(secret_text)

        if self._cache_enabled:
            self._cached_key = key_bytes

        return key_bytes
