from __future__ import annotations

from agentos.domain.sources import Sensitivity


class SensitivityClassifier:
    def classify(self, text: str) -> Sensitivity:
        return Sensitivity.INTERNAL
