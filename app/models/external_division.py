from datetime import datetime, timezone
from typing import Optional

from beanie import Document
from pydantic import Field


class ExternalDivision(Document):
    external_id: str
    name: str
    description: Optional[str] = None
    company_id: Optional[str] = None
    last_synced_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "external_divisions"
        indexes = ["external_id", "company_id", "name"]
