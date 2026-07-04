from __future__ import annotations

from agentos.domain.sources import Sensitivity

_RESTRICTED_TERMS = ("restricted", "classified", "secret")
_CONFIDENTIAL_TERMS = ("confidential", "personal data", "pii", "ssn", "passport")


class SensitivityClassifier:
    def classify(self, text: str) -> Sensitivity:
        lowered = text.lower()
        if any(term in lowered for term in _RESTRICTED_TERMS):
            return Sensitivity.RESTRICTED
        if any(term in lowered for term in _CONFIDENTIAL_TERMS):
            return Sensitivity.CONFIDENTIAL
        return Sensitivity.INTERNAL
