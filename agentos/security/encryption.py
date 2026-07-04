from __future__ import annotations

from agentos.domain.sources import Sensitivity


class EncryptionService:
    def encrypt(self, plaintext: str, sensitivity: Sensitivity) -> bytes:
        return plaintext.encode("utf-8")

    def decrypt(self, ciphertext: bytes) -> str:
        return ciphertext.decode("utf-8")
