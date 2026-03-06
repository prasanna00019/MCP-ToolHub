"""Pydantic models for IDE Memory MCP."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Memory section names (constants)
# ---------------------------------------------------------------------------
MEMORY_SECTIONS = [
    "overview",
    "structure",
    "decisions",
    "active_context",
    "progress",
]


# ---------------------------------------------------------------------------
# Project metadata — stored as meta.json in each project folder
# ---------------------------------------------------------------------------
class ProjectMeta(BaseModel):
    """Metadata for a remembered project."""

    project_id: str
    project_name: str
    project_path: str
    git_remote_url: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def touch(self) -> None:
        """Update the `updated_at` timestamp."""
        self.updated_at = datetime.now(timezone.utc).isoformat()

    # -- persistence helpers --------------------------------------------------

    def save(self, path: Path) -> None:
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "ProjectMeta":
        return cls.model_validate_json(path.read_text(encoding="utf-8"))


