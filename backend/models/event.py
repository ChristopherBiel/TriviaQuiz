import datetime as _dt
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

import re
import uuid


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class EventModel(BaseModel):
    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the event",
        alias="id",
    )
    name: str = Field(..., description="Name of the event")
    date: Optional[_dt.date] = Field(None, description="When the event took place")
    location: Optional[str] = Field(None, description="Where the event took place")
    team_score: Optional[float] = Field(None, description="Original team score")
    best_score: Optional[float] = Field(None, description="Best replay score")
    max_score: Optional[float] = Field(None, description="Maximum possible score")
    description: Optional[str] = Field(None, description="Description of the event")
    language: Optional[str] = Field(None, description="Default language for questions in this event")
    question_ids: list[str] = Field(
        default_factory=list,
        description="Ordered list of question UUIDs belonging to this event",
    )
    created_by: str = Field(..., description="Username of the creator")
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("*", mode="before")
    def strip_and_sanitize_all_strings(cls, v):
        if isinstance(v, str):
            v = v.strip()
            v = re.sub(r"<script.*?>.*?</script>", "", v, flags=re.IGNORECASE | re.DOTALL)
        return v
