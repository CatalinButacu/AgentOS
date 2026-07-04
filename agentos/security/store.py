from __future__ import annotations

from dataclasses import replace

from agentos.domain.sources import EvidenceSpan, Sensitivity
from agentos.security.encryption import EncryptionService
from agentos.security.policy import PolicyGuard


class SecureEvidenceStore:
    def __init__(self, encryption: EncryptionService, policy: PolicyGuard) -> None:
        self.encryption = encryption
        self.policy = policy
        self.ciphertext_by_id: dict[str, bytes] = {}
        self.metadata_by_id: dict[str, EvidenceSpan] = {}

    def put(self, span: EvidenceSpan) -> None:
        self.ciphertext_by_id[span.id] = self.encryption.encrypt(span.text, span.sensitivity)
        self.metadata_by_id[span.id] = replace(span, text="")

    def get_permitted(self, span_ids: list[str], requester_role: str) -> list[EvidenceSpan]:
        permitted: list[EvidenceSpan] = []
        for span_id in span_ids:
            metadata = self.metadata_by_id.get(span_id)
            if metadata is None:
                continue
            if not self.policy.may_access(metadata.sensitivity, requester_role):
                continue
            plaintext = self.encryption.decrypt(self.ciphertext_by_id[span_id])
            permitted.append(replace(metadata, text=plaintext))
        return permitted
