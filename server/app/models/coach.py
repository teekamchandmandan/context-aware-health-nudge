from pydantic import BaseModel, Field


class CoachNudgeItem(BaseModel):
    nudge_id: str
    member_id: str
    member_name: str
    nudge_type: str
    visible_food_summary: str | None = None
    content: str | None = None
    explanation: str | None = None
    matched_reason: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    confidence_factors: list[dict] | None = None
    escalation_recommended: bool = False
    status: str
    latest_action: str | None = None
    phrasing_source: str = "template"
    created_at: str


class CoachNudgeListResponse(BaseModel):
    items: list[CoachNudgeItem]
    limit: int
    count: int


class CoachEscalationItem(BaseModel):
    escalation_id: str
    member_id: str
    member_name: str
    reason: str | None = None
    source: str | None = None
    status: str
    created_at: str


class CoachEscalationListResponse(BaseModel):
    items: list[CoachEscalationItem]
    limit: int
    count: int