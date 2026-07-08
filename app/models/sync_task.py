from datetime import datetime, timezone
from typing import Any, Dict, Optional

from beanie import Document
from pydantic import Field


class SyncTask(Document):
    """Background task state for external employee sync."""

    task_type: str = "employee_sync"
    status: str = "queued"
    progress: int = 0
    message: str = "Sinkronisasi employee sedang diproses"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    class Settings:
        name = "sync_tasks"
        indexes = ["task_type", "status", "created_at"]
