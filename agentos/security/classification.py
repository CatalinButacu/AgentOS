from __future__ import annotations

from collections.abc import Sequence

from agentos.domain.sources import Sensitivity

SensitivityRule = tuple[Sensitivity, tuple[str, ...]]

DEFAULT_SENSITIVITY_RULES: tuple[SensitivityRule, ...] = (
    (Sensitivity.RESTRICTED, ("restricted", "classified", "secret")),
    (Sensitivity.CONFIDENTIAL, ("confidential", "personal data", "pii", "ssn", "passport")),
)


class SensitivityClassifier:
    def __init__(self, rules: Sequence[SensitivityRule] | None = None,
                 unclassified: Sensitivity = Sensitivity.INTERNAL) -> None:
        self.rules = tuple(rules) if rules is not None else DEFAULT_SENSITIVITY_RULES
        self.unclassified = unclassified

    def classify(self, text: str) -> Sensitivity:
        lowered = text.lower()
        for sensitivity, terms in self.rules:
            if any(term in lowered for term in terms):
                return sensitivity
        return self.unclassified
