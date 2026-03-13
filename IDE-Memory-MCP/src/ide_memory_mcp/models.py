"""Pydantic models for IDE Memory MCP."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


# Default sections created for every new project.
# Custom sections beyond these are fully supported — just pass any valid name to update_memory.
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

    # Per-section last-updated timestamps — key: section name, value: ISO timestamp
    sections_updated: dict[str, str] = Field(default_factory=dict)

    def touch(self) -> None:
        """Update the project-level `updated_at` timestamp."""
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def touch_section(self, section: str) -> None:
        """Record that a specific section was just written."""
        self.sections_updated[section] = datetime.now(timezone.utc).isoformat()

    def section_age_days(self, section: str) -> Optional[float]:
        """Return how many days ago a section was last updated, or None if never."""
        ts = self.sections_updated.get(section)
        if not ts:
            return None
        try:
            updated = datetime.fromisoformat(ts)
            delta = datetime.now(timezone.utc) - updated
            return round(delta.total_seconds() / 86400, 1)
        except ValueError:
            return None

    def save(self, path: Path) -> None:
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "ProjectMeta":
        return cls.model_validate_json(path.read_text(encoding="utf-8"))