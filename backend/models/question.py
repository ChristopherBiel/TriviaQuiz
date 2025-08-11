from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
import uuid
import re

class QuestionModel(BaseModel):
    question_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the question")
    question: str = Field(..., description="The question text to display")
    answer: str = Field(..., description="The correct answer")
    added_by: str = Field(..., description="Username of the person who added the question")
    added_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the question was added")
    question_topic: Optional[str] = Field(None, description="Topic/category of the question (for categorization, very broad)")
    question_source: Optional[str] = Field(None, description="Source of the question (e.g. an event)")
    answer_source: Optional[str] = Field(None, description="Source of the answer (e.g. a book or website)")

    incorrect_answers: List[str] = Field(default_factory=list, description="List of incorrect answers for the question")
    times_asked: int = Field(default=0, description="Number of times this question has been asked")
    times_correct: int = Field(default=0, description="Number of times this question has been answered correctly")
    times_incorrect: int = Field(default=0, description="Number of times this question has been answered incorrectly")

    update_history: List[dict] = Field(default_factory=list, description="Revision history of the question")
    last_updated_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the question was last updated")

    language: Optional[str] = Field(None, description="Language of the question (e.g. English, Spanish)")
    tags: List[str] = Field(default_factory=list, description="Tags/categories for filtering")
    review_status: bool = Field(default=False, description="Whether the question is approved for display")
    media_url: Optional[str] = Field(None, description="Optional media file URL")

    @field_validator("*", mode="before")
    def strip_and_sanitize_all_strings(cls, v):
        """Trim whitespace and remove script tags from all string fields."""
        if isinstance(v, str):
            v = v.strip()
            v = re.sub(r"<script.*?>.*?</script>", "", v, flags=re.IGNORECASE | re.DOTALL)
        return v

    @field_validator("tags", mode="before")
    def normalize_tags(cls, v):
        """Ensure tags are lowercase and stripped."""
        if not v:
            return []
        return [tag.strip().lower() for tag in v if isinstance(tag, str) and tag.strip()]

    @field_validator("language", mode="before")
    def normalize_language(cls, v):
        """Lowercase language codes/names."""
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @field_validator("incorrect_answers", mode="before")
    def clean_incorrect_answers(cls, v):
        """Strip and sanitize incorrect answers."""
        if isinstance(v, list):
            cleaned = []
            for ans in v:
                if isinstance(ans, str) and ans.strip():
                    ans = re.sub(r"<script.*?>.*?</script>", "", ans.strip(), flags=re.IGNORECASE | re.DOTALL)
                    cleaned.append(ans)
            return cleaned
        return v

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
