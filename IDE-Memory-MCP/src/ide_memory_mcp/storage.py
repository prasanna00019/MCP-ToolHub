"""
Core storage engine for IDE Memory MCP.

Manages reading / writing project memory files to:
    ~/.ide-memory/projects/<project_id>/

Filesystem layout per project:
    <project_id>/
        meta.json          — project metadata (name, path, timestamps)
        overview.md        — project overview content
        decisions.md       — architectural decisions
        active_context.md  — current working context
        progress.md        — development milestones
        <custom>.md        — any custom sections the agent creates
        .history/          — auto-saved snapshots before each overwrite
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ide_memory_mcp.models import MEMORY_SECTIONS, ProjectMeta


DEFAULT_MEMORY_ROOT = Path.home() / ".ide-memory" / "projects"

# Section names must be lowercase letters/digits/underscores, start with a letter.
_SECTION_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,49}$")

# Number of historical snapshots to keep per section
HISTORY_KEEP = 5


# ---------------------------------------------------------------------------
# Path / URL helpers
# ---------------------------------------------------------------------------

def _make_project_id(project_path: str) -> str:
    """Deterministic short hash from the normalized project path."""
    return hashlib.sha256(_normalize_path(project_path).encode()).hexdigest()[:12]


def _normalize_path(path: str) -> str:
    """Normalize a file path for consistent comparison.

    Handles: case differences on Windows, forward/back slashes, trailing slashes.
    """
    p = Path(path).resolve()
    normalized = str(p).replace("\\", "/")
    if os.name == "nt":
        normalized = normalized.lower()
    return normalized.rstrip("/")


def _normalize_git_url(url: str) -> str:
    """Normalize a git remote URL for comparison.

    Handles:
      - SSH vs HTTPS: git@github.com:user/repo → github.com/user/repo
      - .git suffix: repo.git → repo
      - Trailing slashes
    """
    url = url.strip().rstrip("/").lower()
    if url.endswith(".git"):
        url = url[:-4]
    if url.startswith("git@"):
        url = url[4:].replace(":", "/", 1)
    for prefix in ("https://", "http://", "ssh://"):
        if url.startswith(prefix):
            url = url[len(prefix):]
            break
    return url


def is_valid_section_name(name: str) -> bool:
    """Return True if name is safe to use as a section / filename."""
    return bool(_SECTION_NAME_RE.match(name))


# ---------------------------------------------------------------------------
# Git remote detection
# ---------------------------------------------------------------------------

def _detect_git_remote(project_path: str) -> Optional[str]:
    """Read the git remote URL directly from .git/config — no subprocess, never hangs.

    Walks up the directory tree to find .git/config, then parses the
    [remote "origin"] section to extract the URL.
    """
    import configparser

    path = Path(project_path).resolve()
    for candidate in [path, *path.parents]:
        git_config = candidate / ".git" / "config"
        if git_config.exists():
            try:
                config = configparser.ConfigParser()
                config.read(git_config, encoding="utf-8")
                section = 'remote "origin"'
                if config.has_option(section, "url"):
                    url = config.get(section, "url").strip()
                    return url or None
            except Exception:
                pass
            break  # Found .git but couldn't parse — stop looking

    return None


async def _detect_git_remote_async(project_path: str) -> Optional[str]:
    """Async wrapper — runs the sync parser in a thread to avoid blocking."""
    return await asyncio.to_thread(_detect_git_remote, project_path)


# ---------------------------------------------------------------------------
# MemoryStorage
# ---------------------------------------------------------------------------

class MemoryStorage:
    """Filesystem-backed storage for project memories."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or DEFAULT_MEMORY_ROOT
        self.root.mkdir(parents=True, exist_ok=True)

    # -- directory helpers ---------------------------------------------------

    def _project_dir(self, project_id: str) -> Path:
        return self.root / project_id

    def _meta_path(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "meta.json"

    def _section_path(self, project_id: str, section: str) -> Path:
        return self._project_dir(project_id) / f"{section}.md"

    def _history_dir(self, project_id: str) -> Path:
        return self._project_dir(project_id) / ".history"

    # -- project CRUD --------------------------------------------------------

    def init_project(
        self,
        project_path: str,
        project_name: Optional[str] = None,
        git_remote_url: Optional[str] = None,
    ) -> tuple[ProjectMeta, bool]:
        """Register or reconnect to a project.

        Returns (meta, is_new). Does NOT create the user's project directory —
        we only manage our own storage under ~/.ide-memory/.
        """
        # Auto-detect git remote if not provided (pure file read, never blocks)
        if git_remote_url is None:
            git_remote_url = _detect_git_remote(project_path)

        # Try to find an existing project by path or git remote
        existing = self._find_project(project_path, git_remote_url)
        if existing is not None:
            # Auto-update path if project was found by git remote (folder moved)
            if _normalize_path(existing.project_path) != _normalize_path(project_path):
                existing.project_path = project_path
            # Auto-update git remote if we now have one and didn't before
            if git_remote_url and not existing.git_remote_url:
                existing.git_remote_url = git_remote_url
            existing.touch()
            existing.save(self._meta_path(existing.project_id))
            return existing, False

        # Create new project entry
        project_id = _make_project_id(project_path)
        pdir = self._project_dir(project_id)
        pdir.mkdir(parents=True, exist_ok=True)

        name = project_name or Path(project_path).name
        meta = ProjectMeta(
            project_id=project_id,
            project_name=name,
            project_path=project_path,
            git_remote_url=git_remote_url,
        )
        meta.save(self._meta_path(project_id))

        # Create empty default section files
        for section in MEMORY_SECTIONS:
            sp = self._section_path(project_id, section)
            if not sp.exists():
                sp.write_text(f"# {section.replace('_', ' ').title()}\n\n", encoding="utf-8")

        return meta, True

    def delete_project(self, project_id: str) -> bool:
        """Permanently delete a project and all its memory. Returns True if deleted."""
        pdir = self._project_dir(project_id)
        if not pdir.exists():
            return False
        shutil.rmtree(pdir)
        return True

    def _find_project(
        self, project_path: str, git_remote_url: Optional[str]
    ) -> Optional[ProjectMeta]:
        """Try to find an existing project by path, then by git remote."""
        all_projects = self.list_projects()
        norm_path = _normalize_path(project_path)

        for p in all_projects:
            if _normalize_path(p.project_path) == norm_path:
                return p

        if git_remote_url:
            norm_remote = _normalize_git_url(git_remote_url)
            for p in all_projects:
                if p.git_remote_url and _normalize_git_url(p.git_remote_url) == norm_remote:
                    return p

        return None

    def resolve_project(self, identifier: str) -> Optional[ProjectMeta]:
        """Resolve a project from either a project ID or an absolute path."""
        meta = self.get_project(identifier)
        if meta:
            return meta

        norm_id = _normalize_path(identifier)
        for p in self.list_projects():
            if _normalize_path(p.project_path) == norm_id:
                return p

        return None

    def list_projects(self) -> list[ProjectMeta]:
        """List all known projects."""
        projects: list[ProjectMeta] = []
        if not self.root.exists():
            return projects
        for pdir in self.root.iterdir():
            if pdir.is_dir():
                meta_path = pdir / "meta.json"
                if meta_path.exists():
                    try:
                        projects.append(ProjectMeta.load(meta_path))
                    except Exception:
                        continue
        return projects

    def get_project(self, project_id: str) -> Optional[ProjectMeta]:
        """Get project metadata by ID."""
        meta_path = self._meta_path(project_id)
        if meta_path.exists():
            return ProjectMeta.load(meta_path)
        return None

    def get_all_section_names(self, project_id: str) -> list[str]:
        """Return all section names for a project: default sections first, then custom ones."""
        pdir = self._project_dir(project_id)
        if not pdir.exists():
            return list(MEMORY_SECTIONS)

        found = {f.stem for f in pdir.glob("*.md") if is_valid_section_name(f.stem)}
        ordered = [s for s in MEMORY_SECTIONS if s in found]
        custom = sorted(s for s in found if s not in MEMORY_SECTIONS)
        return ordered + custom

    # -- history -------------------------------------------------------------

    def _save_to_history(self, project_id: str, section: str, current_content: str) -> None:
        """Save the current content of a section to the history folder before overwriting.

        Keeps only the last HISTORY_KEEP snapshots per section.
        """
        if not current_content.strip():
            return  # Nothing worth saving

        hdir = self._history_dir(project_id)
        hdir.mkdir(exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        hist_file = hdir / f"{section}_{timestamp}.md"
        hist_file.write_text(current_content, encoding="utf-8")

        # Prune old snapshots — keep newest HISTORY_KEEP
        snapshots = sorted(hdir.glob(f"{section}_*.md"))
        for old in snapshots[:-HISTORY_KEEP]:
            try:
                old.unlink()
            except OSError:
                pass

    def get_section_history(
        self, project_id: str, section: str, limit: int = 5
    ) -> list[tuple[str, str]]:
        """Return up to `limit` previous snapshots as (timestamp_str, content) pairs, newest first."""
        hdir = self._history_dir(project_id)
        if not hdir.exists():
            return []

        snapshots = sorted(hdir.glob(f"{section}_*.md"), reverse=True)[:limit]
        results: list[tuple[str, str]] = []
        for snap in snapshots:
            # Filename: <section>_YYYYMMDD_HHMMSS.md → extract timestamp part
            raw_ts = snap.stem[len(section) + 1:]  # strip "<section>_"
            try:
                dt = datetime.strptime(raw_ts, "%Y%m%d_%H%M%S").replace(tzinfo=timezone.utc)
                ts_str = dt.strftime("%Y-%m-%d %H:%M UTC")
            except ValueError:
                ts_str = raw_ts
            results.append((ts_str, snap.read_text(encoding="utf-8")))
        return results

    # -- memory section CRUD -------------------------------------------------

    def get_section(self, project_id: str, section: str) -> str:
        """Read a single memory section. Returns empty string if not found."""
        sp = self._section_path(project_id, section)
        if sp.exists():
            return sp.read_text(encoding="utf-8")
        return ""

    def get_section_size(self, project_id: str, section: str) -> int:
        """Return the character count of a section without reading full content into memory."""
        sp = self._section_path(project_id, section)
        if sp.exists():
            return sp.stat().st_size
        return 0

    def update_section(self, project_id: str, section: str, content: str) -> None:
        """Overwrite a memory section with new content.

        Automatically saves the previous content to history before overwriting,
        and updates per-section and project-level timestamps.
        """
        pdir = self._project_dir(project_id)
        pdir.mkdir(parents=True, exist_ok=True)

        # Save existing content to history before overwriting
        sp = self._section_path(project_id, section)
        if sp.exists():
            self._save_to_history(project_id, section, sp.read_text(encoding="utf-8"))

        sp.write_text(content, encoding="utf-8")

        # Update timestamps
        meta = self.get_project(project_id)
        if meta:
            meta.touch()
            meta.touch_section(section)
            meta.save(self._meta_path(project_id))

    def append_to_section(
        self,
        project_id: str,
        section: str,
        content: str,
        heading: str = "",
    ) -> None:
        """Append a new timestamped entry to a section without a full rewrite.

        Use this for decisions, progress notes, or any log-style additions.
        The agent doesn't need to read the existing content first.
        """
        existing = self.get_section(project_id, section)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        if not existing.strip():
            existing = f"# {section.replace('_', ' ').title()}\n"

        if heading:
            new_entry = f"\n\n### {heading}\n_Added: {timestamp}_\n\n{content}"
        else:
            new_entry = f"\n\n---\n_Added: {timestamp}_\n\n{content}"

        self.update_section(project_id, section, existing + new_entry)

    def load_all_memory(self, project_id: str) -> dict[str, str]:
        """Load all memory sections (default + custom) for a project."""
        result: dict[str, str] = {}
        for section in self.get_all_section_names(project_id):
            content = self.get_section(project_id, section)
            if content.strip():
                result[section] = content
        return result

    def load_sections(self, project_id: str, sections: list[str]) -> dict[str, str]:
        """Load only the requested sections. Skips invalid or missing ones."""
        result: dict[str, str] = {}
        for section in sections:
            if not is_valid_section_name(section):
                continue
            content = self.get_section(project_id, section)
            if content.strip():
                result[section] = content
        return result

    def update_multiple_sections(
        self, project_id: str, sections: dict[str, str]
    ) -> tuple[list[str], list[str]]:
        """Update multiple sections at once. Custom section names are allowed.

        Returns (updated_sections, invalid_names).
        """
        updated: list[str] = []
        invalid: list[str] = []

        for section, content in sections.items():
            if not is_valid_section_name(section):
                invalid.append(section)
                continue
            self.update_section(project_id, section, content)
            updated.append(section)

        return updated, invalid

    # -- search --------------------------------------------------------------

    def search_memory(
        self, project_id: str, query: str, context_lines: int = 1
    ) -> dict[str, list[str]]:
        """Keyword search across all memory sections.

        Returns a dict of {section: [matched_snippets]}.
        Each snippet includes `context_lines` lines before/after the match.
        Matches are capped at 8 per section to avoid flooding the response.
        """
        results: dict[str, list[str]] = {}
        query_lower = query.lower()

        for section in self.get_all_section_names(project_id):
            content = self.get_section(project_id, section)
            if not content:
                continue

            lines = content.splitlines()
            snippets: list[str] = []
            seen_ranges: list[tuple[int, int]] = []

            for i, line in enumerate(lines):
                if query_lower not in line.lower():
                    continue

                start = max(0, i - context_lines)
                end = min(len(lines) - 1, i + context_lines)

                # Skip if this range overlaps with a previously captured one
                overlap = any(s <= end and e >= start for s, e in seen_ranges)
                if overlap:
                    continue

                seen_ranges.append((start, end))
                snippet = "\n".join(lines[start : end + 1]).strip()
                snippets.append(snippet)

                if len(snippets) >= 8:
                    break

            if snippets:
                results[section] = snippets

        return results