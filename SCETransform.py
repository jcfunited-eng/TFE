"""
SCETransform.py
-----------------------------------------
UF / SCE-style reversible transform to apply BEFORE AES-GCM.

Purpose:
- Provide a keyed, reversible structural transform of JSON-like payloads.
- Act as a UF-native "semantic encoding" layer above standard cryptography.
- If AES-GCM is intact, attackers never see this.
- If AES-GCM is weakened or bypassed, this layer still distorts the data.

Important:
- This is NOT claimed as a standalone secure cipher.
- It is a deterministic, reversible transform keyed by a secret and context.
- It is intended to layer *before* AES-GCM, not replace it.
"""

from __future__ import annotations

import base64
import hashlib
import json
import random
from dataclasses import dataclass
from typing import Any, Dict, Mapping


@dataclass
class SCETransform:
    """
    SCETransform

    A keyed, reversible transform operating on JSON-serializable mappings.

    - secret: a bytes key known only to the UF / SES-Core layer.
    - rounds: number of mixing rounds (default 3).

    High-level idea:
    1. Canonicalize payload into JSON (sorted keys, fixed separators).
    2. Derive a deterministic pseudo-random sequence from (secret, context).
    3. Use that sequence to:
       - Permute byte positions.
       - Generate a keystream to XOR with bytes.
    4. Base64-url encode the result as a string.

    The inverse operation:
    - Uses the same (secret, context) to rebuild the permutation and keystream.
    - XORs and un-permutes to recover the original JSON bytes.
    - Parses JSON back into a Python dict.
    """

    secret: bytes
    rounds: int = 3

    def __post_init__(self) -> None:
        if not isinstance(self.secret, (bytes, bytearray)):
            raise TypeError("secret must be bytes")
        if len(self.secret) < 16:
            raise ValueError("secret must be at least 16 bytes")
        if self.rounds <= 0:
            raise ValueError("rounds must be positive")

    # -----------------------------
    # Public API
    # -----------------------------

    def encode(self, payload: Mapping[str, Any], context: str) -> str:
        """
        Transform a mapping into a base64 string under the given context.
        """
        canonical = self._canonical_json_bytes(payload)
        mixed = self._permute_and_xor(canonical, context)
        return self._b64encode(mixed)

    def decode(self, encoded: str, context: str) -> Dict[str, Any]:
        """
        Reverse the transform and return the original mapping.
        """
        mixed = self._b64decode(encoded)
        restored = self._unpermute_and_xor(mixed, context)
        obj = json.loads(restored.decode("utf-8"))
        if not isinstance(obj, dict):
            raise ValueError("decoded JSON is not an object")
        return obj

    # -----------------------------
    # Internal helpers
    # -----------------------------

    @staticmethod
    def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
        """
        Canonical JSON: sorted keys, no extra whitespace.
        """
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        data = json.dumps(
            payload,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return data

    @staticmethod
    def _b64encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    @staticmethod
    def _b64decode(data: str) -> bytes:
        padded = data + "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(padded.encode("ascii"))

    def _seed_for_context(self, context: str) -> int:
        """
        Derive an integer seed from (secret, context).
        """
        h = hashlib.sha256()
        h.update(self.secret)
        h.update(context.encode("utf-8"))
        digest = h.digest()
        # Take first 8 bytes as big-endian integer seed
        return int.from_bytes(digest[:8], "big", signed=False)

    def _build_permutation(self, length: int, context: str) -> Dict[int, int]:
        """
        Build a deterministic permutation of indices [0..length-1]
        based on the context and secret.
        """
        if length <= 0:
            return {}

        seed = self._seed_for_context(context)
        rng = random.Random(seed)

        indices = list(range(length))
        for _ in range(self.rounds):
            rng.shuffle(indices)

        # perm[i] = j means new[i] = original[j]
        perm = {i: j for i, j in enumerate(indices)}
        return perm

    def _build_inverse_permutation(self, perm: Dict[int, int]) -> Dict[int, int]:
        """
        inverse_perm[j] = i where perm[i] = j.
        """
        return {j: i for i, j in perm.items()}

    def _keystream(self, length: int, context: str) -> bytes:
        """
        Generate a pseudo-random keystream of 'length' bytes
        derived from (secret, context).
        """
        if length <= 0:
            return b""

        # Start from SHA-256(secret || context) and iterate.
        seed_hash = hashlib.sha256(self.secret + context.encode("utf-8")).digest()
        out = bytearray()
        counter = 0

        while len(out) < length:
            h = hashlib.sha256()
            h.update(seed_hash)
            h.update(counter.to_bytes(4, "big", signed=False))
            block = h.digest()
            out.extend(block)
            counter += 1

        return bytes(out[:length])

    def _permute_and_xor(self, data: bytes, context: str) -> bytes:
        """
        Apply permutation and XOR keystream to data.
        """
        n = len(data)
        if n == 0:
            return b""

        perm = self._build_permutation(n, context)
        ks = self._keystream(n, context)

        # First permute bytes.
        permuted = bytearray(n)
        for new_idx in range(n):
            original_idx = perm[new_idx]
            permuted[new_idx] = data[original_idx]

        # Then XOR with keystream.
        mixed = bytearray(n)
        for i in range(n):
            mixed[i] = permuted[i] ^ ks[i]

        return bytes(mixed)

    def _unpermute_and_xor(self, mixed: bytes, context: str) -> bytes:
        """
        Reverse XOR and permutation.
        """
        n = len(mixed)
        if n == 0:
            return b""

        perm = self._build_permutation(n, context)
        inverse_perm = self._build_inverse_permutation(perm)
        ks = self._keystream(n, context)

        # First reverse XOR.
        unxored = bytearray(n)
        for i in range(n):
            unxored[i] = mixed[i] ^ ks[i]

        # Then reverse permutation.
        restored = bytearray(n)
        for new_idx in range(n):
            original_idx = perm[new_idx]
            restored[original_idx] = unxored[new_idx]

        return bytes(restored)
