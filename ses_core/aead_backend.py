from __future__ import annotations

from typing import Optional

from .envelope import AEADBackend

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError as exc:
    raise ImportError(
        "The 'cryptography' package is required for AESGCMBackend. "
        "Install it with: pip install cryptography"
    ) from exc


class AESGCMBackend(AEADBackend):
    """
    AEADBackend implementation using AES-GCM from the 'cryptography' library.

    Requirements:
    - key: 16, 24, or 32 bytes.
    - nonce: 12 bytes (recommended for AES-GCM).
    """

    def encrypt(
        self,
        key: bytes,
        nonce: bytes,
        plaintext: bytes,
        associated_data: bytes,
    ) -> bytes:
        if not isinstance(key, (bytes, bytearray)):
            raise TypeError("key must be bytes")
        if not isinstance(nonce, (bytes, bytearray)):
            raise TypeError("nonce must be bytes")
        if not isinstance(plaintext, (bytes, bytearray)):
            raise TypeError("plaintext must be bytes")
        if not isinstance(associated_data, (bytes, bytearray)):
            raise TypeError("associated_data must be bytes")

        aesgcm = AESGCM(key)
        return aesgcm.encrypt(
            nonce=nonce,
            data=bytes(plaintext),
            associated_data=bytes(associated_data),
        )

    def decrypt(
        self,
        key: bytes,
        nonce: bytes,
        ciphertext: bytes,
        associated_data: bytes,
    ) -> bytes:
        if not isinstance(key, (bytes, bytearray)):
            raise TypeError("key must be bytes")
        if not isinstance(nonce, (bytes, bytearray)):
            raise TypeError("nonce must be bytes")
        if not isinstance(ciphertext, (bytes, bytearray)):
            raise TypeError("ciphertext must be bytes")
        if not isinstance(associated_data, (bytes, bytearray)):
            raise TypeError("associated_data must be bytes")

        aesgcm = AESGCM(key)
        return aesgcm.decrypt(
            nonce=nonce,
            data=bytes(ciphertext),
            associated_data=bytes(associated_data),
        )
