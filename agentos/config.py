from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from agentos.domain.sources import Sensitivity
from agentos.identity.roles import ROLE_CLEARANCE, SENSITIVITY_RANK, Role
from agentos.security.classification import (DEFAULT_SENSITIVITY_RULES,
                                             SensitivityRule)


@dataclass(frozen=True)
class ComplianceConfig:
    groundedness_threshold: float = 0.7
    support_threshold: float = 0.6
    contradiction_penalty: float = 0.5
    token_budget: int = 2000
    semantic_recall: int = 5
    unclassified_sensitivity: Sensitivity = Sensitivity.INTERNAL
    sensitivity_rules: Sequence[SensitivityRule] = DEFAULT_SENSITIVITY_RULES
    sensitivity_rank: Mapping[Sensitivity, int] = field(
        default_factory=lambda: dict(SENSITIVITY_RANK))
    role_clearances: Mapping[Role, Sensitivity] = field(
        default_factory=lambda: dict(ROLE_CLEARANCE))
