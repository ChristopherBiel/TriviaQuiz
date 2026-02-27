from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict
import uuid


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class UserModel(BaseModel):
    user_id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="id")
    username: str
    email: str
    password_hash: str
    role: str = "user"
    is_verified: bool = False
    is_approved: bool = False
    verification_token: str | None = None
    verification_expires_at: datetime | None = None
    reset_token: str | None = None
    reset_expires_at: datetime | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    last_login_at: datetime | None = None
    last_login_ip: str | None = None

    model_config = ConfigDict(populate_by_name=True)
