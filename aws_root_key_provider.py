from __future__ import annotations

import base64
import os
from typing import Optional

# RootKeyProvider comes from the SES-Core package, not a top-level module.
from ses_core import RootKeyProvider  # type: ignore[import]


DEFAULT_CONNECT_TIMEOUT_SECONDS = 3
DEFAULT_READ_TIMEOUT_SECONDS = 5
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_CACHE_PATH = "tfe_root_key.bin"


def _env_int(
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    raw = str(os.environ.get(name, "")).strip()
    if not raw:
        return default

    try:
        value = int(raw)
    except Exception:
        return default

    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


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
    SES-Core RootKeyProvider that loads the root key from AWS Secrets Manager.

    Expected configuration (environment variables):

      * TFE_SES_ROOT_SECRET_ID  - name or ARN of the secret that holds the root key
      * AWS_REGION              - AWS region for Secrets Manager (e.g. 'us-east-1')

    The secret value may be:
      * hex string (preferred); or
      * base64 string; or
      * raw UTF-8 string of at least 32 bytes.
    """

    def __init__(
        self,
        secret_id: Optional[str] = None,
        region_name: Optional[str] = None,
        cache: bool = True,
        cache_file_path: Optional[str] = None,
        connect_timeout_seconds: Optional[int] = None,
        read_timeout_seconds: Optional[int] = None,
        max_attempts: Optional[int] = None,
    ) -> None:
        self._secret_id = secret_id or os.environ.get("TFE_SES_ROOT_SECRET_ID", "")
        self._region_name = region_name or os.environ.get("AWS_REGION", "")
        self._cache_enabled = cache
        self._cache_file_path = str(
            cache_file_path
            or os.environ.get("TFE_SES_ROOT_KEY_CACHE_PATH", DEFAULT_CACHE_PATH)
        ).strip()
        self._connect_timeout_seconds = (
            connect_timeout_seconds
            if connect_timeout_seconds is not None
            else _env_int(
                "TFE_AWS_SECRETS_CONNECT_TIMEOUT_SECONDS",
                DEFAULT_CONNECT_TIMEOUT_SECONDS,
                1,
                30,
            )
        )
        self._read_timeout_seconds = (
            read_timeout_seconds
            if read_timeout_seconds is not None
            else _env_int(
                "TFE_AWS_SECRETS_READ_TIMEOUT_SECONDS",
                DEFAULT_READ_TIMEOUT_SECONDS,
                1,
                60,
            )
        )
        self._max_attempts = (
            max_attempts
            if max_attempts is not None
            else _env_int(
                "TFE_AWS_SECRETS_MAX_ATTEMPTS",
                DEFAULT_MAX_ATTEMPTS,
                1,
                10,
            )
        )
        self._cached_key: Optional[bytes] = None

    @classmethod
    def from_env(cls, *, cache: bool = True) -> "AwsSecretsRootKeyProvider":
        """
        Construct a provider directly from runtime environment variables.
        """
        return cls(
            secret_id=os.environ.get("TFE_SES_ROOT_SECRET_ID", ""),
            region_name=os.environ.get("AWS_REGION", ""),
            cache=cache,
            cache_file_path=os.environ.get("TFE_SES_ROOT_KEY_CACHE_PATH", DEFAULT_CACHE_PATH),
            connect_timeout_seconds=_env_int(
                "TFE_AWS_SECRETS_CONNECT_TIMEOUT_SECONDS",
                DEFAULT_CONNECT_TIMEOUT_SECONDS,
                1,
                30,
            ),
            read_timeout_seconds=_env_int(
                "TFE_AWS_SECRETS_READ_TIMEOUT_SECONDS",
                DEFAULT_READ_TIMEOUT_SECONDS,
                1,
                60,
            ),
            max_attempts=_env_int(
                "TFE_AWS_SECRETS_MAX_ATTEMPTS",
                DEFAULT_MAX_ATTEMPTS,
                1,
                10,
            ),
        )

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

        config = None
        try:
            from botocore.config import Config  # type: ignore

            config = Config(
                connect_timeout=self._connect_timeout_seconds,
                read_timeout=self._read_timeout_seconds,
                retries={
                    "max_attempts": self._max_attempts,
                    "mode": "standard",
                },
            )
        except Exception:
            config = None

        # Region is optional; if empty, boto3 will fall back to its default chain.
        if config is None:
            client = boto3.client(
                "secretsmanager",
                region_name=self._region_name or None,
            )
        else:
            client = boto3.client(
                "secretsmanager",
                region_name=self._region_name or None,
                config=config,
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
          * raw utf-8 (length >= 32)
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

        # Fallback: raw utf-8
        b = text.encode("utf-8")
        if len(b) < 32:
            raise ValueError(
                "AWS root key secret must be at least 32 bytes "
                "(after decoding)."
            )
        return b

    def _load_cached_key_from_file(self) -> Optional[bytes]:
        if not self._cache_file_path:
            return None

        try:
            with open(self._cache_file_path, "rb") as f:
                data = f.read()
        except Exception:
            return None

        if len(data) < 32:
            return None

        return data

    def _write_cached_key_to_file(self, key_bytes: bytes) -> None:
        if not self._cache_file_path:
            return

        parent_dir = os.path.dirname(self._cache_file_path)
        if parent_dir and parent_dir != ".":
            try:
                os.makedirs(parent_dir, exist_ok=True)
            except Exception:
                return

        try:
            fd = os.open(
                self._cache_file_path,
                os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
                0o600,
            )
            with os.fdopen(fd, "wb") as f:
                f.write(key_bytes)
            try:
                os.chmod(self._cache_file_path, 0o600)
            except Exception:
                pass
        except Exception:
            pass

    # ------------------------
    # RootKeyProvider interface
    # ------------------------
    def get_root_key(self) -> bytes:  # type: ignore[override]
        """
        Return the root key bytes for SES-Core HKDF.

        This is cached in-process if cache=True.
        """
        if self._cache_enabled and self._cached_key is not None:
            return self._cached_key

        if self._cache_enabled:
            key_from_file = self._load_cached_key_from_file()
            if key_from_file is not None:
                self._cached_key = key_from_file
                return key_from_file

        secret_text = self._load_secret_string()
        key_bytes = self._parse_secret_bytes(secret_text)

        if self._cache_enabled:
            self._cached_key = key_bytes
            self._write_cached_key_to_file(key_bytes)

        return key_bytes
