import datetime as _dt
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

import re
import uuid


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class LiveSessionModel(BaseModel):
    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the live session",
    )
    event_id: str = Field(..., description="Event being presented")
    join_code: str = Field(..., description="Short code for players to join")
    current_question_index: int = Field(
        default=-1, description="-1 = lobby, 0+ = active question index"
    )
    revealed_indices: list[int] = Field(
        default_factory=list,
        description="Question indices whose answers have been revealed",
    )
    locked_indices: list[int] = Field(
        default_factory=list,
        description="Question indices where answers are locked",
    )
    show_questions_on_devices: bool = Field(
        default=False,
        description="Whether players see question text on their devices",
    )
    status: str = Field(
        default="lobby", description="lobby / active / finished"
    )
    created_by: str = Field(..., description="Username of the presenter")
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("*", mode="before")
    def strip_and_sanitize_all_strings(cls, v):
        if isinstance(v, str):
            v = v.strip()
            v = re.sub(
                r"<script.*?>.*?</script>", "", v, flags=re.IGNORECASE | re.DOTALL
            )
        return v


class LiveParticipantModel(BaseModel):
    participant_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the participant",
    )
    session_id: str = Field(..., description="Live session this participant belongs to")
    display_name: str = Field(..., description="Name shown on leaderboard")
    user_id: Optional[str] = Field(
        None, description="User ID if logged in, None for anonymous"
    )
    joined_at: datetime = Field(default_factory=_utcnow)

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("*", mode="before")
    def strip_and_sanitize_all_strings(cls, v):
        if isinstance(v, str):
            v = v.strip()
            v = re.sub(
                r"<script.*?>.*?</script>", "", v, flags=re.IGNORECASE | re.DOTALL
            )
        return v


class LiveAnswerModel(BaseModel):
    answer_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this answer",
    )
    session_id: str = Field(..., description="Live session")
    participant_id: str = Field(..., description="Participant who answered")
    question_index: int = Field(..., description="Index into event.question_ids")
    answer_text: str = Field(default="", description="The participant's answer")
    is_locked: bool = Field(default=False, description="Whether the answer is locked")
    points_awarded: Optional[float] = Field(None, description="Points after evaluation")
    max_points: Optional[float] = Field(None, description="Max possible points")
    is_correct: Optional[bool] = Field(None, description="Whether the answer is correct")
    explanation: Optional[str] = Field(None, description="Evaluation explanation")
    submitted_at: datetime = Field(default_factory=_utcnow)

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("*", mode="before")
    def strip_and_sanitize_all_strings(cls, v):
        if isinstance(v, str):
            v = v.strip()
            v = re.sub(
                r"<script.*?>.*?</script>", "", v, flags=re.IGNORECASE | re.DOTALL
            )
        return v
