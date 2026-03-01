from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

import uuid


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ReplayAttemptModel(BaseModel):
    replay_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the replay attempt",
        alias="id",
    )
    event_id: str = Field(..., description="Event being replayed")
    user_id: Optional[str] = Field(None, description="User ID (null for anonymous)")
    display_name: Optional[str] = Field(None, description="Display name for leaderboard")
    score: int = Field(..., description="Number of correct answers")
    total: int = Field(..., description="Total number of questions")
    answers: list[dict] = Field(
        default_factory=list,
        description="List of answer details: [{question_id, user_answer, correct_answer, is_correct}]",
    )
    completed_at: datetime = Field(default_factory=_utcnow)

    model_config = ConfigDict(populate_by_name=True)
