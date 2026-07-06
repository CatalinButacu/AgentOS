from __future__ import annotations

from enum import Enum

from agentos.domain.sources import Sensitivity


class Role(str, Enum):
    CLERK = "clerk"
    TEAM_LEADER = "team_leader"
    MANAGER = "manager"
    PRODUCT_OWNER = "product_owner"
    OWNER = "owner"
    BOARD_MEMBER = "board_member"


SENSITIVITY_RANK = {
    Sensitivity.PUBLIC: 0,
    Sensitivity.INTERNAL: 1,
    Sensitivity.CONFIDENTIAL: 2,
    Sensitivity.RESTRICTED: 3,
}

ROLE_CLEARANCE = {
    Role.CLERK: Sensitivity.INTERNAL,
    Role.TEAM_LEADER: Sensitivity.CONFIDENTIAL,
    Role.MANAGER: Sensitivity.CONFIDENTIAL,
    Role.PRODUCT_OWNER: Sensitivity.CONFIDENTIAL,
    Role.OWNER: Sensitivity.RESTRICTED,
    Role.BOARD_MEMBER: Sensitivity.INTERNAL,
}
