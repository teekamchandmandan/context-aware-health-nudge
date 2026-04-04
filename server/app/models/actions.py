from pydantic import BaseModel

from .shared import ActionType


class ActionRequest(BaseModel):
    action_type: ActionType


class ActionResponse(BaseModel):
    nudge_id: str
    action_type: str
    nudge_status: str
    escalation_created: bool
    recorded_at: str