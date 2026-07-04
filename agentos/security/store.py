from __future__ import annotations

from dataclasses import replace

from agentos.domain.sources import EvidenceSpan
from agentos.identity.principal import Principal
from agentos.ingestion.dedup import ContentDeduper
from agentos.security.encryption import EncryptionService
from agentos.security.policy import PolicyGuard


class SecureEvidenceStore:
    def __init__(self, encryption: EncryptionService, policy: PolicyGuard,
                 deduper: ContentDeduper | None = None) -> None:
        self.encryption = encryption
        self.policy = policy
        self.deduper = deduper or ContentDeduper()
        self.ciphertext_by_hash: dict[str, bytes] = {}
        self.span_by_id: dict[str, EvidenceSpan] = {}

    def put(self, span: EvidenceSpan) -> None:
        content_hash = span.metadata.content_hash
        if self.deduper.is_new(content_hash):
            self.ciphertext_by_hash[content_hash] = self.encryption.encrypt(
                span.text, span.metadata.sensitivity)
        self.span_by_id[span.id] = replace(span, text="")

    def get_permitted(self, span_ids: list[str], principal: Principal) -> list[EvidenceSpan]:
        permitted: list[EvidenceSpan] = []
        for span_id in span_ids:
            stored = self.span_by_id.get(span_id)
            if stored is None:
                continue
            if not self.policy.may_access(principal, stored.metadata.sensitivity,
                                          stored.metadata.tenant_id):
                continue
            plaintext = self.encryption.decrypt(self.ciphertext_by_hash[stored.metadata.content_hash])
            permitted.append(replace(stored, text=plaintext))
        return permitted
