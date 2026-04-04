from __future__ import annotations

from pydantic import BaseModel

from .shared import MemberRef, NudgeDetail, NudgeState


class MemberNudgeResponse(BaseModel):
    state: NudgeState
    member: MemberRef
    nudge: NudgeDetail | None = None
    escalation_created: bool | None = None