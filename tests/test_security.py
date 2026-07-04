import pickle
from dataclasses import replace

import pytest

from agentos.domain.sources import Sensitivity
from agentos.identity.access import AccessPolicy
from agentos.identity.principal import Principal
from agentos.identity.roles import Role
from agentos.ingestion.chunker import Chunker
from agentos.security.classification import SensitivityClassifier
from agentos.security.encryption import EncryptionService
from agentos.security.policy import PolicyGuard
from agentos.security.store import SecureEvidenceStore


def test_clearance_by_role():
    policy = AccessPolicy()
    assert policy.may_access(Principal("c", {Role.CLERK}), Sensitivity.INTERNAL)
    assert not policy.may_access(Principal("c", {Role.CLERK}), Sensitivity.CONFIDENTIAL)
    assert policy.may_access(Principal("o", {Role.OWNER}), Sensitivity.RESTRICTED)
    assert not policy.may_access(Principal("b", {Role.BOARD_MEMBER}), Sensitivity.CONFIDENTIAL)


def test_tenant_abac():
    policy = AccessPolicy()
    principal = Principal("o", {Role.OWNER}, tenant_id="t1")
    assert policy.may_access(principal, Sensitivity.INTERNAL, tenant_id="t1")
    assert not policy.may_access(principal, Sensitivity.INTERNAL, tenant_id="t2")
    assert policy.may_access(principal, Sensitivity.INTERNAL, tenant_id=None)


def test_classifier_keywords():
    classifier = SensitivityClassifier()
    assert classifier.classify("personal data on file") == Sensitivity.CONFIDENTIAL
    assert classifier.classify("this is restricted") == Sensitivity.RESTRICTED
    assert classifier.classify("a general note") == Sensitivity.INTERNAL


def test_store_encrypts_and_gates_by_role():
    store = SecureEvidenceStore(EncryptionService(), PolicyGuard())
    span = Chunker().chunk("doc.s", "s", "1", "Personal data here.")[0]
    confidential = replace(span, metadata=replace(span.metadata, sensitivity=Sensitivity.CONFIDENTIAL))
    store.put(confidential)
    stored = pickle.loads(store.backend.get("spans", confidential.id))
    assert stored.text == ""
    owner = store.get_permitted([confidential.id], Principal("o", {Role.OWNER}))
    clerk = store.get_permitted([confidential.id], Principal("c", {Role.CLERK}))
    assert owner and owner[0].text == "Personal data here."
    assert clerk == []


def test_encryption_round_trip():
    service = EncryptionService()
    ciphertext = service.encrypt("secret text", Sensitivity.CONFIDENTIAL)
    assert b"secret text" not in ciphertext
    assert service.decrypt(ciphertext, Sensitivity.CONFIDENTIAL) == "secret text"


def test_encryption_rejects_wrong_sensitivity():
    service = EncryptionService()
    ciphertext = service.encrypt("secret text", Sensitivity.CONFIDENTIAL)
    with pytest.raises(Exception):
        service.decrypt(ciphertext, Sensitivity.PUBLIC)


def test_encryption_rejects_tampered_ciphertext():
    service = EncryptionService()
    ciphertext = bytearray(service.encrypt("secret text", Sensitivity.INTERNAL))
    ciphertext[-1] ^= 1
    with pytest.raises(Exception):
        service.decrypt(bytes(ciphertext), Sensitivity.INTERNAL)
