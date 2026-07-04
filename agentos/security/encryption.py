from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from agentos.domain.sources import Sensitivity

_DEV_KEY = b"agentos-dev-key-0123456789abcdef"
_NONCE_SIZE = 12


class EncryptionService:
    def __init__(self, key: bytes | None = None) -> None:
        self._cipher = AESGCM(key or _DEV_KEY)

    @classmethod
    def from_env(cls) -> "EncryptionService":
        raw = os.environ.get("AGENTOS_ENCRYPTION_KEY")
        return cls(base64.b64decode(raw)) if raw else cls()

    @classmethod
    def from_key_vault(cls, vault_url: str, secret_name: str) -> "EncryptionService":
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient
        except ImportError as error:
            raise RuntimeError(
                "azure-keyvault-secrets and azure-identity are required for Key Vault keys") from error
        client = SecretClient(vault_url=vault_url, credential=DefaultAzureCredential())
        return cls(base64.b64decode(client.get_secret(secret_name).value))

    def encrypt(self, plaintext: str, sensitivity: Sensitivity) -> bytes:
        nonce = os.urandom(_NONCE_SIZE)
        ciphertext = self._cipher.encrypt(nonce, plaintext.encode("utf-8"),
                                          sensitivity.value.encode("utf-8"))
        return nonce + ciphertext

    def decrypt(self, ciphertext: bytes, sensitivity: Sensitivity) -> str:
        nonce, body = ciphertext[:_NONCE_SIZE], ciphertext[_NONCE_SIZE:]
        plaintext = self._cipher.decrypt(nonce, body, sensitivity.value.encode("utf-8"))
        return plaintext.decode("utf-8")
