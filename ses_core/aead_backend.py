from __future__ import annotations

import hashlib
import hmac
import math
from typing import Tuple

from .envelope import AEADBackend

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError as exc:
    raise ImportError(
        "The 'cryptography' package is required for SES AEAD backends. "
        "Install it with: pip install cryptography"
    ) from exc


class AESGCMBackend(AEADBackend):
    """
    Legacy AES-GCM backend retained for backward decrypt compatibility.

    Requirements:
    - key: 16, 24, or 32 bytes.
    - nonce: 12 bytes.
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

        aesgcm = AESGCM(bytes(key))
        return aesgcm.encrypt(
            nonce=bytes(nonce),
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

        aesgcm = AESGCM(bytes(key))
        return aesgcm.decrypt(
            nonce=bytes(nonce),
            data=bytes(ciphertext),
            associated_data=bytes(associated_data),
        )


class SCESIVBackend(AEADBackend):
    """
    SCE-SIV v1.0 deterministic AEAD backend.

    Implements the SCE-SIV profile from `SCE_Specification_v1_0.pdf`:
    - SIV = BLAKE2s_k(AD || nonce || H(P))
    - k_enc = HKDF(master_key, "SCE-SIV-EXTRACT", "SCE-SIV-ENC" || SIV)
    - Keystream from the canonical structural engine + mosaic compression
    - Tag = BLAKE2s_k(AD || nonce || C || SIV)

    Ciphertext wire format returned by encrypt():
      b"TFE-SCE-SIV-v1\x00" || SIV(32) || TAG(32) || C
    """

    _PREFIX = b"TFE-SCE-SIV-v1\x00"
    _SIV_LEN = 32
    _TAG_LEN = 32

    _G = 8
    _D = 4
    _T = 4
    _ALPHA = 1.5
    _BETA = 0.5
    _SEED_LEN = 256

    def encrypt(
        self,
        key: bytes,
        nonce: bytes,
        plaintext: bytes,
        associated_data: bytes,
    ) -> bytes:
        master_key = self._require_bytes("key", key)
        nonce_bytes = self._require_bytes("nonce", nonce)
        plain = self._require_bytes("plaintext", plaintext)
        aad = self._require_bytes("associated_data", associated_data)

        siv = self._derive_siv(master_key=master_key, aad=aad, nonce=nonce_bytes, plaintext=plain)
        k_enc = self._derive_k_enc(master_key=master_key, siv=siv)
        keystream = self._generate_keystream(
            k_enc=k_enc,
            nonce=nonce_bytes,
            aad=aad,
            siv=siv,
            out_len=len(plain),
        )
        cipher = self._xor_bytes(plain, keystream)
        tag = self._derive_tag(master_key=master_key, aad=aad, nonce=nonce_bytes, ciphertext=cipher, siv=siv)

        return self._PREFIX + siv + tag + cipher

    def decrypt(
        self,
        key: bytes,
        nonce: bytes,
        ciphertext: bytes,
        associated_data: bytes,
    ) -> bytes:
        master_key = self._require_bytes("key", key)
        nonce_bytes = self._require_bytes("nonce", nonce)
        blob = self._require_bytes("ciphertext", ciphertext)
        aad = self._require_bytes("associated_data", associated_data)

        if not blob.startswith(self._PREFIX):
            raise ValueError("SCE ciphertext prefix missing")

        min_len = len(self._PREFIX) + self._SIV_LEN + self._TAG_LEN
        if len(blob) < min_len:
            raise ValueError("SCE ciphertext payload is truncated")

        offset = len(self._PREFIX)
        siv = blob[offset : offset + self._SIV_LEN]
        offset += self._SIV_LEN
        tag = blob[offset : offset + self._TAG_LEN]
        offset += self._TAG_LEN
        cipher = blob[offset:]

        k_enc = self._derive_k_enc(master_key=master_key, siv=siv)
        keystream = self._generate_keystream(
            k_enc=k_enc,
            nonce=nonce_bytes,
            aad=aad,
            siv=siv,
            out_len=len(cipher),
        )
        plain = self._xor_bytes(cipher, keystream)

        recomputed_siv = self._derive_siv(master_key=master_key, aad=aad, nonce=nonce_bytes, plaintext=plain)
        recomputed_tag = self._derive_tag(
            master_key=master_key,
            aad=aad,
            nonce=nonce_bytes,
            ciphertext=cipher,
            siv=recomputed_siv,
        )

        if not hmac.compare_digest(recomputed_siv, siv):
            raise ValueError("SCE SIV verification failed")
        if not hmac.compare_digest(recomputed_tag, tag):
            raise ValueError("SCE tag verification failed")

        return plain

    @staticmethod
    def _require_bytes(name: str, value: bytes) -> bytes:
        if not isinstance(value, (bytes, bytearray)):
            raise TypeError(f"{name} must be bytes")
        return bytes(value)

    @staticmethod
    def _hkdf_extract(salt: bytes, ikm: bytes) -> bytes:
        return hmac.new(salt, ikm, hashlib.sha256).digest()

    @staticmethod
    def _hkdf_expand(prk: bytes, info: bytes, length: int) -> bytes:
        if length <= 0:
            raise ValueError("HKDF length must be positive")

        digest_size = hashlib.sha256().digest_size
        n = (length + digest_size - 1) // digest_size
        if n > 255:
            raise ValueError("HKDF length too large")

        output = bytearray()
        block = b""
        for i in range(1, n + 1):
            block = hmac.new(prk, block + info + bytes([i]), hashlib.sha256).digest()
            output.extend(block)
        return bytes(output[:length])

    @staticmethod
    def _xor_bytes(left: bytes, right: bytes) -> bytes:
        if len(left) != len(right):
            raise ValueError("XOR operands must have identical length")
        return bytes(a ^ b for a, b in zip(left, right))

    def _derive_siv(self, master_key: bytes, aad: bytes, nonce: bytes, plaintext: bytes) -> bytes:
        payload_hash = hashlib.blake2s(plaintext, digest_size=self._SIV_LEN).digest()
        siv_input = aad + nonce + payload_hash
        return hashlib.blake2s(siv_input, key=master_key, digest_size=self._SIV_LEN).digest()

    def _derive_tag(self, master_key: bytes, aad: bytes, nonce: bytes, ciphertext: bytes, siv: bytes) -> bytes:
        tag_input = aad + nonce + ciphertext + siv
        return hashlib.blake2s(tag_input, key=master_key, digest_size=self._TAG_LEN).digest()

    def _derive_k_enc(self, master_key: bytes, siv: bytes) -> bytes:
        prk = self._hkdf_extract(salt=b"SCE-SIV-EXTRACT", ikm=master_key)
        return self._hkdf_expand(prk=prk, info=b"SCE-SIV-ENC" + siv, length=32)

    def _derive_engine_seed(self, k_enc: bytes, nonce: bytes, aad: bytes, siv: bytes) -> bytes:
        prk_eng = self._hkdf_extract(salt=b"SCE-ENGINE-SEED", ikm=k_enc)
        info = b"SCE-ENGINE-CTX" + nonce + aad + siv
        return self._hkdf_expand(prk=prk_eng, info=info, length=self._SEED_LEN)

    @staticmethod
    def _xof_stream(seed: bytes, out_len: int) -> bytes:
        out = bytearray()
        counter = 0
        while len(out) < out_len:
            block = hashlib.blake2s(seed + counter.to_bytes(8, "big"), digest_size=32).digest()
            out.extend(block)
            counter += 1
        return bytes(out[:out_len])

    @staticmethod
    def _int32_to_unit(raw4: bytes) -> float:
        signed = int.from_bytes(raw4, byteorder="big", signed=True)
        min_i32 = -(1 << 31)
        max_i32 = (1 << 31) - 1
        if signed == min_i32:
            value = -1.0
        else:
            value = signed / float(max_i32)
        if value > 1.0:
            return 1.0
        if value < -1.0:
            return -1.0
        return value

    def _fill_matrix(self, stream: bytes, offset: int, rows: int, cols: int) -> Tuple[list[list[float]], int]:
        matrix: list[list[float]] = []
        for _ in range(rows):
            row: list[float] = []
            for _ in range(cols):
                if offset + 4 > len(stream):
                    raise ValueError("Seed stream exhausted during matrix fill")
                value = self._int32_to_unit(stream[offset : offset + 4])
                row.append(value)
                offset += 4
            matrix.append(row)
        return matrix, offset

    def _seed_to_state_and_params(
        self,
        seed: bytes,
    ) -> Tuple[
        list[list[float]],
        list[list[float]],
        list[list[float]],
        list[list[float]],
        list[list[float]],
        list[list[float]],
        list[list[float]],
        list[list[float]],
    ]:
        g = self._G
        d = self._D

        total_floats = (
            g * d  # X0
            + g * d  # Y0 (consumed, then overwritten by -X0)
            + g * g  # W_x
            + g * g  # W_y
            + g * d  # B_x
            + g * d  # B_y
            + g * g  # C_xy
            + g * g  # C_yx
        )
        stream = self._xof_stream(seed=seed, out_len=total_floats * 4)

        offset = 0
        x_state, offset = self._fill_matrix(stream=stream, offset=offset, rows=g, cols=d)
        y_state, offset = self._fill_matrix(stream=stream, offset=offset, rows=g, cols=d)
        w_x, offset = self._fill_matrix(stream=stream, offset=offset, rows=g, cols=g)
        w_y, offset = self._fill_matrix(stream=stream, offset=offset, rows=g, cols=g)
        b_x, offset = self._fill_matrix(stream=stream, offset=offset, rows=g, cols=d)
        b_y, offset = self._fill_matrix(stream=stream, offset=offset, rows=g, cols=d)
        c_xy, offset = self._fill_matrix(stream=stream, offset=offset, rows=g, cols=g)
        c_yx, _ = self._fill_matrix(stream=stream, offset=offset, rows=g, cols=g)

        # Section 4.3.3: enforce negative-space initialization relation.
        for gate in range(g):
            for j in range(d):
                y_state[gate][j] = -x_state[gate][j]

        return x_state, y_state, w_x, w_y, b_x, b_y, c_xy, c_yx

    @staticmethod
    def _clip_unit(value: float) -> float:
        if value > 1.0:
            return 1.0
        if value < -1.0:
            return -1.0
        return value

    def _step_engine(
        self,
        x_state: list[list[float]],
        y_state: list[list[float]],
        w_x: list[list[float]],
        w_y: list[list[float]],
        b_x: list[list[float]],
        b_y: list[list[float]],
        c_xy: list[list[float]],
        c_yx: list[list[float]],
    ) -> Tuple[list[list[float]], list[list[float]]]:
        g = self._G
        d = self._D

        x_tilde = [[0.0 for _ in range(d)] for _ in range(g)]
        y_tilde = [[0.0 for _ in range(d)] for _ in range(g)]

        for out_gate in range(g):
            for in_gate in range(g):
                wx = w_x[out_gate][in_gate]
                wy = w_y[out_gate][in_gate]
                cxy = c_xy[out_gate][in_gate]
                cyx = c_yx[out_gate][in_gate]

                x_in = x_state[in_gate]
                y_in = y_state[in_gate]

                for j in range(d):
                    x_tilde[out_gate][j] += wx * x_in[j] + cxy * y_in[j]
                    y_tilde[out_gate][j] += wy * y_in[j] + cyx * x_in[j]

            for j in range(d):
                x_tilde[out_gate][j] += b_x[out_gate][j]
                y_tilde[out_gate][j] += b_y[out_gate][j]

        x_next = [[0.0 for _ in range(d)] for _ in range(g)]
        y_next = [[0.0 for _ in range(d)] for _ in range(g)]

        for gate in range(g):
            for j in range(d):
                fold_x = self._BETA * (x_state[gate][j] - y_state[gate][j])
                fold_y = self._BETA * (y_state[gate][j] - x_state[gate][j])

                x_val = math.tanh(self._ALPHA * x_tilde[gate][j]) + fold_x
                y_val = math.tanh(self._ALPHA * y_tilde[gate][j]) + fold_y

                x_next[gate][j] = self._clip_unit(x_val)
                y_next[gate][j] = self._clip_unit(y_val)

        return x_next, y_next

    def _mosaic_bytes(self, x_state: list[list[float]], y_state: list[list[float]]) -> bytes:
        g = self._G
        d = self._D

        out = bytearray(g * d * 4)

        def quantize(value: float) -> int:
            v = self._clip_unit(value)
            q = int(math.floor(((v + 1.0) / 2.0) * 255.0))
            if q < 0:
                return 0
            if q > 255:
                return 255
            return q

        for gate in range(g):
            vx = x_state[gate]
            vy = y_state[gate]

            for j in range(d):
                out.append(quantize(vx[j]))
            for j in range(d):
                out.append(quantize(vy[j]))
            for j in range(d):
                out.append(quantize(vx[j] - vy[j]))
            for j in range(d):
                out.append(quantize(vx[j] * vy[j]))

        return bytes(out)

    def _generate_keystream(
        self,
        k_enc: bytes,
        nonce: bytes,
        aad: bytes,
        siv: bytes,
        out_len: int,
    ) -> bytes:
        if out_len < 0:
            raise ValueError("out_len must be non-negative")
        if out_len == 0:
            return b""

        seed = self._derive_engine_seed(k_enc=k_enc, nonce=nonce, aad=aad, siv=siv)
        x_state, y_state, w_x, w_y, b_x, b_y, c_xy, c_yx = self._seed_to_state_and_params(seed=seed)

        prk_block = self._hkdf_extract(salt=b"SCE-BLOCK-EXTRACT", ikm=k_enc)
        k_block = self._hkdf_expand(prk=prk_block, info=b"SCE-BLOCK-KEY", length=32)

        out = bytearray()
        block_index = 0

        while len(out) < out_len:
            mosaics = bytearray()
            for _ in range(self._T):
                x_state, y_state = self._step_engine(
                    x_state=x_state,
                    y_state=y_state,
                    w_x=w_x,
                    w_y=w_y,
                    b_x=b_x,
                    b_y=b_y,
                    c_xy=c_xy,
                    c_yx=c_yx,
                )
                mosaics.extend(self._mosaic_bytes(x_state=x_state, y_state=y_state))

            block_input = b"SCE-BLOCK" + block_index.to_bytes(8, "big") + bytes(mosaics)
            block = hashlib.blake2s(block_input, key=k_block, digest_size=32).digest()
            out.extend(block)
            block_index += 1

        return bytes(out[:out_len])
