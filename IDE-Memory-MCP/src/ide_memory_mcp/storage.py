"""
Core storage engine for IDE Memory MCP.

Manages reading / writing project memory files to:
    ~/.ide-memory/projects/<project_id>/
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Optional

from ide_memory_mcp.models import MEMORY_SECTIONS, ProjectMeta


DEFAULT_MEMORY_ROOT = Path.home() / ".ide-memory" / "projects"


def _make_project_id(project_path: str) -> str:
    """Deterministic short hash from the normalized project path."""
    return hashlib.sha256(_normalize_path(project_path).encode()).hexdigest()[:12]


def _normalize_path(path: str) -> str:
    """Normalize a file path for consistent comparison.

    Handles: case differences on Windows, forward/back slashes, trailing slashes.
    """
    p = Path(path).resolve()
    # Use forward slashes, lowercase on Windows for consistent hashing
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
    url = url.strip().rstrip("/")
    # Remove .git suffix
    if url.endswith(".git"):
        url = url[:-4]
    # Convert SSH to path format: git@github.com:user/repo → github.com/user/repo
    if url.startswith("git@"):
        url = url[4:].replace(":", "/", 1)
    # Strip protocol: https://github.com/user/repo → github.com/user/repo
    for prefix in ("https://", "http://", "ssh://"):
        if url.startswith(prefix):
            url = url[len(prefix):]
            break
    return url.lower()


def _detect_git_remote(project_path: str) -> Optional[str]:
    """Read the git remote URL directly from .git/config — no subprocess, never hangs.

    Walks up the directory tree to find the .git/config file, then parses
    the [remote "origin"] section to extract the URL.
    """
    import configparser

    # Walk up from project_path looking for .git/config
    path = Path(project_path).resolve()
    for candidate in [path, *path.parents]:
        git_config = candidate / ".git" / "config"
        if git_config.exists():
            try:
                config = configparser.ConfigParser()
                config.read(git_config, encoding="utf-8")
                # ConfigParser key: 'remote "origin"'
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




class MemoryStorage:
    """Filesystem-backed storage for project memories."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or DEFAULT_MEMORY_ROOT
        self.root.mkdir(parents=True, exist_ok=True)

    # -- project directory helpers -------------------------------------------

    def _project_dir(self, project_id: str) -> Path:
        return self.root / project_id

    def _meta_path(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "meta.json"

    def _section_path(self, project_id: str, section: str) -> Path:
        return self._project_dir(project_id) / f"{section}.md"

    # -- project CRUD --------------------------------------------------------

    def init_project(
        self,
        project_path: str,
        project_name: Optional[str] = None,
        git_remote_url: Optional[str] = None,
    ) -> tuple[ProjectMeta, bool]:
        """
        Register or reconnect to a project.

        Returns (meta, is_new).  If the project already exists we just
        return its metadata; otherwise we create a fresh entry.
        """
        # Create the project directory if it doesn't exist
        Path(project_path).mkdir(parents=True, exist_ok=True)

        # Auto-detect git remote if not provided (pure file read, never blocks)
        if git_remote_url is None:
            git_remote_url = _detect_git_remote(project_path)

        # Try to find an existing project
        existing = self._find_project(project_path, git_remote_url)
        if existing is not None:
            # Auto-update path if project was found by git remote (folder moved)
            norm_existing = _normalize_path(existing.project_path)
            norm_new = _normalize_path(project_path)
            if norm_existing != norm_new:
                existing.project_path = project_path
            # Auto-update git remote if we now have one and didn't before
            if git_remote_url and not existing.git_remote_url:
                existing.git_remote_url = git_remote_url
            existing.touch()
            existing.save(self._meta_path(existing.project_id))
            return existing, False

        # Create new project
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

        # Create empty section files
        for section in MEMORY_SECTIONS:
            sp = self._section_path(project_id, section)
            if not sp.exists():
                sp.write_text(f"# {section.replace('_', ' ').title()}\n\n", encoding="utf-8")

        return meta, True

    def _find_project(
        self, project_path: str, git_remote_url: Optional[str]
    ) -> Optional[ProjectMeta]:
        """Try to find an existing project by path, then git remote."""
        all_projects = self.list_projects()
        norm_path = _normalize_path(project_path)

        # 1. Normalized path match (case-insensitive on Windows, slash-normalized)
        for p in all_projects:
            if _normalize_path(p.project_path) == norm_path:
                return p

        # 2. Normalized git remote match (SSH/HTTPS/.git agnostic)
        if git_remote_url:
            norm_remote = _normalize_git_url(git_remote_url)
            for p in all_projects:
                if p.git_remote_url and _normalize_git_url(p.git_remote_url) == norm_remote:
                    return p

        return None

    def resolve_project(self, identifier: str) -> Optional[ProjectMeta]:
        """Resolve a project from either an ID or a path.

        Used by tools to accept either format.
        """
        # First try as project ID (direct lookup)
        meta = self.get_project(identifier)
        if meta:
            return meta

        # Then try as a path (search all projects)
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

    # -- memory section CRUD -------------------------------------------------

    def get_section(self, project_id: str, section: str) -> str:
        """Read a single memory section."""
        sp = self._section_path(project_id, section)
        if sp.exists():
            return sp.read_text(encoding="utf-8")
        return ""

    def update_section(self, project_id: str, section: str, content: str) -> None:
        """Overwrite a memory section with new content."""
        pdir = self._project_dir(project_id)
        pdir.mkdir(parents=True, exist_ok=True)
        sp = self._section_path(project_id, section)
        sp.write_text(content, encoding="utf-8")

        # Touch project timestamp
        meta = self.get_project(project_id)
        if meta:
            meta.touch()
            meta.save(self._meta_path(project_id))

    def load_all_memory(self, project_id: str) -> dict[str, str]:
        """Load all memory sections for a project."""
        result: dict[str, str] = {}
        for section in MEMORY_SECTIONS:
            content = self.get_section(project_id, section)
            if content.strip():
                result[section] = content
        return result

    def update_multiple_sections(
        self, project_id: str, sections: dict[str, str]
    ) -> list[str]:
        """Update multiple memory sections at once.  Returns list of updated section names."""
        updated: list[str] = []
        for section, content in sections.items():
            if section in MEMORY_SECTIONS:
                self.update_section(project_id, section, content)
                updated.append(section)
        return updated


# ---------------------------------------------------------------------------
# Directory tree scanner
# ---------------------------------------------------------------------------

# Directories to always skip
IGNORE_DIRS = {
    ".git", ".svn", ".hg",
    "node_modules", ".node_modules",
    "__pycache__", ".pytest_cache", ".mypy_cache",
    ".venv", "venv", "env", ".env",
    ".tox", ".nox",
    "dist", "build", ".eggs", "*.egg-info",
    ".next", ".nuxt", ".output",
    ".idea", ".vscode", ".vs",
    "vendor", "target",
    ".terraform",
}

# File extensions to skip
IGNORE_EXTENSIONS = {
    ".pyc", ".pyo", ".class", ".o", ".so", ".dll", ".exe",
    ".lock", ".sum",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp",
    ".woff", ".woff2", ".ttf", ".eot",
    ".mp3", ".mp4", ".avi", ".mov",
    ".zip", ".tar", ".gz", ".rar",
    ".db", ".sqlite", ".sqlite3",
}


def _should_ignore(name: str, is_dir: bool) -> bool:
    """Check if a file or directory should be ignored."""
    if is_dir:
        return name in IGNORE_DIRS or name.startswith(".")
    # Skip hidden files and known binary extensions
    if name.startswith("."):
        return True
    suffix = Path(name).suffix.lower()
    return suffix in IGNORE_EXTENSIONS


def scan_directory_tree(
    project_path: str,
    max_depth: int = 4,
    max_files: int = 200,
) -> str:
    """
    Scan a project directory and return a markdown tree representation.

    Args:
        project_path: Root directory to scan.
        max_depth: Maximum depth to recurse into.
        max_files: Maximum number of entries to include.

    Returns:
        Markdown-formatted directory tree string.
    """
    root = Path(project_path)
    if not root.exists() or not root.is_dir():
        return f"❌ Path does not exist or is not a directory: {project_path}"

    lines: list[str] = [f"# Project Structure: {root.name}\n", "```"]
    file_count = 0

    def _walk(directory: Path, prefix: str, depth: int) -> None:
        nonlocal file_count
        if depth > max_depth or file_count > max_files:
            return

        try:
            entries = sorted(
                directory.iterdir(),
                key=lambda e: (not e.is_dir(), e.name.lower()),
            )
        except PermissionError:
            return

        # Filter out ignored entries
        entries = [e for e in entries if not _should_ignore(e.name, e.is_dir())]

        for i, entry in enumerate(entries):
            if file_count > max_files:
                lines.append(f"{prefix}... (truncated, >{max_files} entries)")
                return

            is_last = i == len(entries) - 1
            connector = "└── " if is_last else "├── "
            extension = "    " if is_last else "│   "

            if entry.is_dir():
                child_count = sum(1 for _ in entry.iterdir()) if entry.exists() else 0
                lines.append(f"{prefix}{connector}{entry.name}/")
                file_count += 1
                _walk(entry, prefix + extension, depth + 1)
            else:
                # Show file size for context
                try:
                    size = entry.stat().st_size
                    if size < 1024:
                        size_str = f"{size}B"
                    elif size < 1024 * 1024:
                        size_str = f"{size // 1024}KB"
                    else:
                        size_str = f"{size // (1024 * 1024)}MB"
                    lines.append(f"{prefix}{connector}{entry.name} ({size_str})")
                except OSError:
                    lines.append(f"{prefix}{connector}{entry.name}")
                file_count += 1

    _walk(root, "", 0)
    lines.append("```")

    if file_count > max_files:
        lines.append(f"\n> ⚠️ Tree truncated at {max_files} entries. Use a smaller `max_depth` for large projects.")

    lines.append(f"\n**Total entries shown**: {min(file_count, max_files)}")
    return "\n".join(lines)
