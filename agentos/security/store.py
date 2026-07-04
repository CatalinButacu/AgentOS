from __future__ import annotations

import pickle
from dataclasses import replace

from agentos.domain.sources import EvidenceSpan
from agentos.identity.principal import Principal
from agentos.ingestion.dedup import ContentDeduper
from agentos.persistence.kv import InMemoryStore, KeyValueStore
from agentos.security.encryption import EncryptionService
from agentos.security.policy import PolicyGuard

_CIPHERTEXT = "ciphertext"
_SPANS = "spans"


class SecureEvidenceStore:
    def __init__(self, encryption: EncryptionService, policy: PolicyGuard,
                 backend: KeyValueStore | None = None,
                 deduper: ContentDeduper | None = None) -> None:
        self.encryption = encryption
        self.policy = policy
        self.backend = backend or InMemoryStore()
        self.deduper = deduper or ContentDeduper()
        for content_hash, _ in self.backend.items(_CIPHERTEXT):
            self.deduper.is_new(content_hash)

    def put(self, span: EvidenceSpan) -> None:
        content_hash = span.metadata.content_hash
        if self.deduper.is_new(content_hash):
            self.backend.put(_CIPHERTEXT, content_hash,
                             self.encryption.encrypt(span.text, span.metadata.sensitivity))
        self.backend.put(_SPANS, span.id, pickle.dumps(replace(span, text="")))

    def get_permitted(self, span_ids: list[str], principal: Principal) -> list[EvidenceSpan]:
        permitted: list[EvidenceSpan] = []
        for span_id in span_ids:
            raw = self.backend.get(_SPANS, span_id)
            if raw is None:
                continue
            stored = pickle.loads(raw)
            if not self.policy.may_access(principal, stored.metadata.sensitivity,
                                          stored.metadata.tenant_id):
                continue
            ciphertext = self.backend.get(_CIPHERTEXT, stored.metadata.content_hash)
            plaintext = self.encryption.decrypt(ciphertext, stored.metadata.sensitivity)
            permitted.append(replace(stored, text=plaintext))
        return permitted
