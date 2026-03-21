"""
aws_root_key_provider.py
-----------------------------------------
RootKeyProvider implementation that loads the SES-Core root key
from AWS Secrets Manager.

This is only used when running in AWS (e.g. TFE_ENV=aws).
Local/dev environments continue to use the existing behavior.
"""

from __future__ import annotations

import os
import base64
import binascii
from typing import Optional

from key_derivation import RootKeyProvider


class AwsSecretsRootKeyProvider(RootKeyProvider):
    """
    RootKeyProvider that fetches a 256-bit root key from AWS Secrets Manager.

    Configuration (via environment variables):

      - TFE_ROOT_KEY_SECRET_NAME:
          Name or ARN of the secret holding the root key.
          Default: "tfe/root-key"

      - AWS_REGION / AWS_DEFAULT_REGION:
          AWS region where the secret lives (e.g. "us-east-1").

    Secret formats supported:

      - SecretBinary: used directly as bytes
      - SecretString: expected to be a 64-character hex string
                      (representing 32 bytes). If not valid hex, we try
                      base64 decode as a fallback.

    This provider does NOT cache across processes; SES-Core should treat
    get_root_key() as an idempotent call.
    """

    def __init__(self, secret_name: str, region: Optional[str] = None) -> None:
        self._secret_name = secret_name
        self._region = region

    @classmethod
    def from_env(cls) -> "AwsSecretsRootKeyProvider":
        """
        Construct from environment variables only.

        - TFE_ROOT_KEY_SECRET_NAME (optional)
        - AWS_REGION / AWS_DEFAULT_REGION (optional)
        """
        secret_name = os.environ.get("TFE_ROOT_KEY_SECRET_NAME", "tfe/root-key")
        region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
        return cls(secret_name=secret_name, region=region)

    def get_root_key(self) -> bytes:
        """
        Fetch and decode the root key from AWS Secrets Manager.

        Raises:
          - RuntimeError if configuration is missing or the key format is invalid.
        """
        # Import boto3 lazily so local/dev without boto3 still works.
        try:
            import boto3  # type: ignore
        except ImportError as exc:  # pragma: no cover - environment-specific
            raise RuntimeError(
                "boto3 is required to use AwsSecretsRootKeyProvider, "
                "but could not be imported."
            ) from exc

        region = self._region or os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
        if not region:
            raise RuntimeError(
                "AWS region is not set. Please set AWS_REGION or AWS_DEFAULT_REGION."
            )

        client = boto3.client("secretsmanager", region_name=region)

        try:
            resp = client.get_secret_value(SecretId=self._secret_name)
        except Exception as exc:  # pragma: no cover - runtime/aws specific
            raise RuntimeError(
                f"Failed to fetch root key from Secrets Manager secret "
                f"'{self._secret_name}' in region '{region}': {exc}"
            ) from exc

        # Prefer binary if present
        if "SecretBinary" in resp and resp["SecretBinary"] is not None:
            key_bytes = resp["SecretBinary"]
            # In some environments SecretBinary may be base64-encoded bytes.
            if isinstance(key_bytes, str):
                key_bytes = key_bytes.encode("utf-8")
            try:
                # Try base64 decode first; if it fails, assume raw bytes.
                decoded = base64.b64decode(key_bytes, validate=True)
                key_bytes = decoded
            except Exception:
                # Treat as raw bytes; nothing more to do.
                pass
        else:
            secret_str = resp.get("SecretString")
            if secret_str is None:
                raise RuntimeError(
                    f"Secret '{self._secret_name}' has neither SecretBinary "
                    "nor SecretString."
                )

            # First, try hex
            try:
                key_bytes = binascii.unhexlify(secret_str.strip())
            except (binascii.Error, ValueError):
                # Fallback: try base64
                try:
                    key_bytes = base64.b64decode(secret_str, validate=True)
                except Exception as exc:
                    raise RuntimeError(
                        "SecretString must be either a hex string or base64 "
                        f"encoded bytes. Could not decode: {exc}"
                    ) from exc

        if not isinstance(key_bytes, (bytes, bytearray)):
            raise RuntimeError(
                "Root key from Secrets Manager is not bytes."
            )

        if len(key_bytes) != 32:
            raise RuntimeError(
                f"Root key must be 32 bytes (256 bits); got {len(key_bytes)} bytes."
            )

        return bytes(key_bytes)
