"""
IDE Memory MCP Server — Entry point.

A cross-IDE persistent memory layer for AI coding agents.
Run with: uv run ide-memory-mcp

Tool surface (5 tools, down from 11):
  init_project          — register or reconnect to a project (always call first)
  read_memory           — load / search / history / prune (all reads)
  write_memory          — overwrite or append to sections (all writes)
  scan_project_structure — scan directory tree into the structure section
  manage_projects       — list all projects or delete one
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from ide_memory_mcp.storage import MemoryStorage, scan_directory_tree, is_valid_section_name
from ide_memory_mcp.models import MEMORY_SECTIONS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("ide-memory-mcp")

mcp = FastMCP("ide-memory-mcp")
storage = MemoryStorage()


# ---------------------------------------------------------------------------
# Internal helpers (not exposed as tools)
# ---------------------------------------------------------------------------

def _staleness_label(days: float | None) -> str:
    if days is None:
        return "never updated"
    if days < 1:
        return "updated today"
    if days < 2:
        return "updated yesterday"
    return f"updated {int(days)} days ago"


def _resolve(identifier: str):
    """Resolve project or return None."""
    return storage.resolve_project(identifier)


# ===========================================================================
# TOOL 1 — init_project
# ===========================================================================

@mcp.tool()
async def init_project(
    projectPath: str,
    projectName: str = "",
    gitRemoteUrl: str = "",
) -> str:
    """Register or reconnect to a project. Always call this first.

    - New project  → creates memory storage, returns next-step instructions.
    - Known project → reconnects, returns per-section staleness summary.

    Matching priority: exact path → normalized path → git remote URL.
    Git remote is auto-detected from .git/config if not provided.
    Does NOT create the project directory on disk.
    """
    meta, is_new = storage.init_project(
        projectPath,
        projectName or None,
        gitRemoteUrl or None,
    )

    if is_new:
        return (
            f"✅ New project registered!\n\n"
            f"- **ID**: `{meta.project_id}`\n"
            f"- **Name**: {meta.project_name}\n"
            f"- **Path**: {meta.project_path}\n"
            f"- **Git Remote**: {meta.git_remote_url or 'N/A'}\n\n"
            f"Default sections: {', '.join(MEMORY_SECTIONS)}\n\n"
            f"**Next steps**:\n"
            f"1. `scan_project_structure` — auto-capture the directory tree\n"
            f"2. `write_memory` — fill in: overview, decisions, active_context, progress"
        )

    # Reconnect — show per-section staleness
    all_sections = storage.get_all_section_names(meta.project_id)
    section_lines = []
    empty_sections = []

    for s in all_sections:
        content = storage.get_section(meta.project_id, s)
        is_empty = len(content.strip()) < 50
        staleness = _staleness_label(meta.section_age_days(s))
        if is_empty:
            empty_sections.append(s)
            section_lines.append(f"  - `{s}`: ⚠️ empty")
        else:
            section_lines.append(f"  - `{s}`: {len(content)} chars, {staleness}")

    empty_hint = (
        f"\n\n⚠️ Empty sections: {', '.join(empty_sections)}. Use `write_memory` to fill them."
        if empty_sections else ""
    )

    return (
        f"🔗 Reconnected to **{meta.project_name}**\n\n"
        f"- **ID**: `{meta.project_id}`\n"
        f"- **Path**: {meta.project_path}\n"
        f"- **Git Remote**: {meta.git_remote_url or 'N/A'}\n"
        f"- **Last Updated**: {meta.updated_at}\n\n"
        f"**Sections**:\n" + "\n".join(section_lines) +
        empty_hint +
        "\n\nCall `read_memory` to load full context."
    )


# ===========================================================================
# TOOL 2 — read_memory
# ===========================================================================

@mcp.tool()
async def read_memory(
    projectIdOrPath: str,
    section: str = "",
    query: str = "",
    history: bool = False,
    historyLimit: int = 3,
    prune: bool = False,
) -> str:
    """Read project memory. All read operations in one tool.

    Modes (evaluated in priority order):

      query != ""     → search all sections for a keyword or phrase
      history=True    → show previous snapshots of `section` (section required)
      prune=True      → load all sections with agent pruning instructions
      section != ""   → load that one section (includes staleness + stale warning if >14d)
      (default)       → load all sections

    Args:
        projectIdOrPath : project ID or absolute path
        section         : section name — required for history and single-section modes
        query           : keyword/phrase to search across all sections
        history         : if True, return previous snapshots of `section`
        historyLimit    : number of snapshots to return (1–5, default 3)
        prune           : if True, load all sections with pruning instructions
    """
    meta = _resolve(projectIdOrPath)
    if not meta:
        return f"❌ Project `{projectIdOrPath}` not found."

    # --- Mode 1: search ---
    if query:
        results = storage.search_memory(meta.project_id, query.strip())
        if not results:
            return f"🔍 No matches for `{query}` in **{meta.project_name}**."
        total = sum(len(v) for v in results.values())
        parts = [f"🔍 {total} match(es) for `{query}` in **{meta.project_name}**:\n"]
        for sec, snippets in results.items():
            parts.append(f"\n### {sec.replace('_', ' ').title()}\n")
            for snippet in snippets:
                parts.append(f"```\n{snippet}\n```")
        return "\n".join(parts)

    # --- Mode 2: history ---
    if history:
        if not section:
            return "❌ `section` is required when `history=True`."
        if not is_valid_section_name(section):
            return f"❌ Invalid section name: `{section}`."
        limit = max(1, min(historyLimit, 5))
        snapshots = storage.get_section_history(meta.project_id, section, limit)
        if not snapshots:
            return f"📭 No history found for `{section}` in **{meta.project_name}**."
        parts = [
            f"# History: `{section}` — {meta.project_name}\n",
            f"{len(snapshots)} snapshot(s). To restore: copy content → call `write_memory`.\n",
        ]
        for i, (ts, content) in enumerate(snapshots, 1):
            parts.append(f"\n---\n## Snapshot {i} — {ts}\n\n{content}")
        return "\n".join(parts)

    # --- Mode 3: prune ---
    if prune:
        memory = storage.load_all_memory(meta.project_id)
        if not memory:
            return "📭 No memory to prune yet."
        parts = [
            f"# 🧹 Prune: {meta.project_name}\n",
            "Remove: outdated info, contradictions (keep newest), duplicates.\n"
            "Then call `write_memory` with cleaned content for changed sections.\n",
        ]
        for sec, content in memory.items():
            staleness = _staleness_label(meta.section_age_days(sec))
            parts.append(
                f"\n---\n## {sec.replace('_', ' ').title()} _{staleness}_\n\n{content}"
            )
        return "\n".join(parts)

    # --- Mode 4: single section ---
    if section:
        if not is_valid_section_name(section):
            return f"❌ Invalid section name: `{section}`."
        content = storage.get_section(meta.project_id, section)
        if not content.strip():
            return f"📭 Section `{section}` is empty."
        days = meta.section_age_days(section)
        staleness = _staleness_label(days)
        stale_warn = (
            f"\n\n> ⚠️ {int(days)} days old — consider updating."
            if days is not None and days > 14 else ""
        )
        return f"_`{section}` — {staleness}_\n\n{content}{stale_warn}"

    # --- Mode 5: load all (default) ---
    memory = storage.load_all_memory(meta.project_id)
    if not memory:
        return "📭 No memory yet. Use `write_memory` to add context."
    parts = [f"# 🧠 {meta.project_name} — Memory\n"]
    for sec, content in memory.items():
        staleness = _staleness_label(meta.section_age_days(sec))
        parts.append(
            f"\n---\n## {sec.replace('_', ' ').title()} _{staleness}_\n\n{content}"
        )
    return "\n".join(parts)


# ===========================================================================
# TOOL 3 — write_memory
# ===========================================================================

@mcp.tool()
async def write_memory(
    projectIdOrPath: str,
    sections: dict[str, str],
    append: bool = False,
    heading: str = "",
) -> str:
    """Write to one or more memory sections.

    Modes:

      append=False (default) — overwrite sections with full new content.
        Always provide the complete current state, not just a diff.
        Previous content is auto-saved to history before overwriting.

      append=True — add a timestamped entry to the bottom of each section.
        Use for incremental updates: new decisions, progress notes, issues.
        Existing content is preserved — no need to read first.
        `heading` sets an optional heading for the appended entry.

    Default sections: overview, structure, decisions, active_context, progress.
    Custom sections supported — any lowercase identifier (e.g. "api_contracts").

    Args:
        projectIdOrPath : project ID or absolute path
        sections        : {section_name: content}
        append          : if True, append rather than overwrite
        heading         : heading for the appended entry (only used when append=True)
    """
    meta = _resolve(projectIdOrPath)
    if not meta:
        return f"❌ Project `{projectIdOrPath}` not found."

    invalid = [s for s in sections if not is_valid_section_name(s)]
    if invalid:
        return (
            f"❌ Invalid section name(s): {invalid}.\n"
            f"Use lowercase letters, digits, underscores; must start with a letter.\n"
            f"Default sections: {MEMORY_SECTIONS}"
        )

    if append:
        for section, content in sections.items():
            storage.append_to_section(meta.project_id, section, content, heading)
        label = f'under "{heading}"' if heading else "with timestamp"
        return (
            f"✅ Appended to {len(sections)} section(s) {label}: "
            f"{', '.join(sections.keys())}"
        )

    updated, _ = storage.update_multiple_sections(meta.project_id, sections)
    still_empty = [
        s for s in MEMORY_SECTIONS
        if s not in sections and len(storage.get_section(meta.project_id, s).strip()) < 50
    ]
    reminder = f"\n\n💡 Still empty: {', '.join(still_empty)}." if still_empty else ""
    return f"✅ Updated {len(updated)} section(s): {', '.join(updated)}{reminder}"


# ===========================================================================
# TOOL 4 — scan_project_structure
# ===========================================================================

@mcp.tool()
async def scan_project_structure(
    projectIdOrPath: str,
    maxDepth: int = 4,
    maxFiles: int = 200,
    preserveAnnotations: bool = True,
) -> str:
    """Scan the project directory and save the file tree to the 'structure' section.

    Args:
        projectIdOrPath     : project ID or absolute path
        maxDepth            : recursion depth (default 4)
        maxFiles            : max entries to include (default 200)
        preserveAnnotations : carry forward inline <!-- notes --> and any free-text
                              added after the tree block (default True)
    """
    meta = _resolve(projectIdOrPath)
    if not meta:
        return f"❌ Project `{projectIdOrPath}` not found."

    existing = storage.get_section(meta.project_id, "structure") if preserveAnnotations else ""

    tree = scan_directory_tree(
        meta.project_path,
        max_depth=maxDepth,
        max_files=maxFiles,
        existing_structure=existing,
        preserve_annotations=preserveAnnotations,
    )

    storage.update_section(meta.project_id, "structure", tree)

    mode = "annotations preserved" if preserveAnnotations and existing else "fresh scan"
    return (
        f"✅ Structure saved for **{meta.project_name}** ({mode})\n\n{tree}\n\n"
        f"💡 Add `<!-- notes -->` inline or free-text below the tree — "
        f"they survive future rescans."
    )


# ===========================================================================
# TOOL 5 — manage_projects
# ===========================================================================

@mcp.tool()
async def manage_projects(
    action: str,
    projectIdOrPath: str = "",
    confirm: bool = False,
) -> str:
    """List all projects or delete one.

    Actions:
      "list"   — list all registered projects sorted by last updated.
                 projectIdOrPath not required.

      "delete" — permanently delete a project and all its memory.
                 Requires projectIdOrPath + confirm=True.
                 Without confirm=True shows a warning and does nothing.

    Args:
        action          : "list" or "delete"
        projectIdOrPath : project ID or absolute path (required for delete)
        confirm         : must be True to proceed with delete
    """
    if action == "list":
        projects = storage.list_projects()
        if not projects:
            return "📭 No projects registered yet."
        lines = ["# 📋 Registered Projects\n"]
        for p in sorted(projects, key=lambda x: x.updated_at, reverse=True):
            lines.append(
                f"- **{p.project_name}** (`{p.project_id}`)\n"
                f"  - Path: `{p.project_path}`\n"
                f"  - Git: {p.git_remote_url or 'N/A'}\n"
                f"  - Last updated: {p.updated_at}\n"
            )
        return "\n".join(lines)

    if action == "delete":
        if not projectIdOrPath:
            return "❌ `projectIdOrPath` is required for delete."
        meta = _resolve(projectIdOrPath)
        if not meta:
            return f"❌ Project `{projectIdOrPath}` not found."
        if not confirm:
            return (
                f"⚠️ This will permanently delete all memory for **{meta.project_name}** "
                f"(`{meta.project_id}`).\n\nCall again with `confirm=True` to proceed."
            )
        deleted = storage.delete_project(meta.project_id)
        return (
            f"🗑️ Deleted **{meta.project_name}** and all its memory."
            if deleted else
            f"❌ Could not delete `{meta.project_id}`."
        )

    return f"❌ Unknown action `{action}`. Valid: `list`, `delete`."


# ===========================================================================
# RESOURCES
# ===========================================================================

@mcp.resource("memory://{project_id}/{section}")
async def read_memory_resource(project_id: str, section: str) -> str:
    """Read a project memory section as a resource."""
    if not is_valid_section_name(section):
        raise ValueError(f"Invalid section name: {section}")
    return storage.get_section(project_id, section)


# ===========================================================================
# Entry point
# ===========================================================================

def main() -> None:
    logger.info("IDE Memory MCP server starting...")
    logger.info("Memory root: %s", storage.root)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()