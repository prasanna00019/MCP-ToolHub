"""
IDE Memory MCP Server — Entry point.

A cross-IDE persistent memory layer for AI coding agents.
Run with: uv run ide-memory-mcp

Tool surface (4 tools):
  init_project    — register or reconnect to a project (always call first)
  read_memory     — context-aware loading: summary, selective, search, history
  write_memory    — overwrite or append to sections (all writes)
  manage_projects — list all projects or delete one

Prompts (3 agent workflows):
  start_session      — what the agent should do at the start of every conversation
  bootstrap_memory   — populate memory for a project the agent hasn't seen before
  update_memory      — review & update memory after making significant changes
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from ide_memory_mcp.storage import MemoryStorage, is_valid_section_name
from ide_memory_mcp.models import MEMORY_SECTIONS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("ide-memory-mcp")

mcp = FastMCP("ide-memory-mcp")
storage = MemoryStorage()


# Staleness thresholds (days)
STALE_WARNING_DAYS = 7
PRUNE_SUGGESTION_DAYS = 30
LARGE_SECTION_CHARS = 10_000


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


def _format_size(chars: int) -> str:
    """Format character count in a human-readable compact form."""
    if chars < 1_000:
        return f"{chars}"
    if chars < 10_000:
        return f"{chars / 1_000:.1f}k"
    return f"{chars // 1_000}k"


def _truncate(content: str, max_chars: int) -> str:
    """Truncate content to max_chars, preserving line boundaries where possible."""
    if max_chars <= 0 or len(content) <= max_chars:
        return content
    # Try to break at a newline near the limit
    cut = content[:max_chars]
    last_newline = cut.rfind("\n")
    if last_newline > max_chars * 0.7:  # break at newline if reasonably close
        cut = cut[:last_newline]
    return f"{cut}\n\n... _(truncated — showing {len(cut)} of {len(content)} chars)_"


# ===========================================================================
# TOOL 1 — init_project
# ===========================================================================

@mcp.tool()
async def init_project(
    projectPath: str,
    projectName: str = "",
    gitRemoteUrl: str = "",
) -> str:
    """Register or reconnect to a project. ALWAYS call this first in every conversation.

    This is the entry point for all IDE Memory operations. It either:
    - Registers a NEW project → creates memory storage
    - Reconnects to a KNOWN project → returns memory summary with actionable warnings

    Matching priority: exact path → normalized path → git remote URL.
    Git remote is auto-detected from .git/config if not provided.

    IMPORTANT: Call this tool at the START of every conversation before doing any work.
    Use the project's root directory as projectPath.
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
            f"📋 **This is a new project with no memory yet.**\n"
            f"Populate the memory by analyzing the project and calling `write_memory` with:\n"
            f"- `overview`: What this project is, tech stack, architecture\n"
            f"- `decisions`: Key technical decisions and their rationale\n"
            f"- `active_context`: What is currently being worked on\n"
            f"- `progress`: Milestones, completed items, upcoming work\n\n"
            f"💡 Tip: Use the `bootstrap_memory` prompt for a guided walkthrough."
        )

    # Reconnect — return smart summary with warnings
    return _build_summary(meta)


# ===========================================================================
# TOOL 2 — read_memory
# ===========================================================================

@mcp.tool()
async def read_memory(
    projectIdOrPath: str,
    sections: list[str] | None = None,
    query: str = "",
    maxChars: int = 0,
    history: bool = False,
    historyLimit: int = 3,
    prune: bool = False,
) -> str:
    """Read project memory. Context-aware — loads only what you need.

    Modes (evaluated in priority order):

      query != ""       → search all sections for a keyword/phrase
      history=True      → show previous snapshots of a section (pass ONE section name in `sections`)
      prune=True        → load all sections with agent pruning instructions
      sections=[...]    → load only the listed sections (most common usage)
      (default)         → return a compact summary table (names, sizes, staleness — NO content)

    IMPORTANT — Smart loading workflow:
      1. Call with no sections → get the summary table (minimal context cost)
      2. Decide which sections are relevant to the current task
      3. Call again with sections=["overview", "decisions"] to load only what you need

    This prevents flooding your context window with unnecessary information.

    Args:
        projectIdOrPath : project ID or absolute path
        sections        : section names to load — omit for summary mode
        query           : keyword/phrase to search across all sections
        maxChars        : max characters per section (0 = unlimited). Useful for previews.
        history         : if True, return previous snapshots (requires exactly one section)
        historyLimit    : number of snapshots to return (1–5, default 3)
        prune           : if True, load all sections with pruning instructions
    """
    meta = _resolve(projectIdOrPath)
    if not meta:
        return f"❌ Project `{projectIdOrPath}` not found."

    # --- Mode 1: search ---
    if query:
        return _search_mode(meta, query.strip())

    # --- Mode 2: history ---
    if history:
        if not sections or len(sections) != 1:
            return "❌ Provide exactly one section name in `sections` when `history=True`."
        section = sections[0]
        if not is_valid_section_name(section):
            return f"❌ Invalid section name: `{section}`."
        return _history_mode(meta, section, historyLimit)

    # --- Mode 3: prune ---
    if prune:
        return _prune_mode(meta)

    # --- Mode 4: selective load ---
    if sections:
        return _selective_load(meta, sections, maxChars)

    # --- Mode 5: summary (DEFAULT — no content dumped) ---
    return _build_summary(meta)


def _build_summary(meta) -> str:
    """Build a compact summary table with smart warnings.

    Includes actionable alerts for:
    - Empty sections that need to be filled
    - Stale sections (>7 days) that should be updated
    - Large sections (>10k chars) that may need pruning
    - Very old sections (>30 days) that suggest a full prune
    """
    all_sections = storage.get_all_section_names(meta.project_id)

    if not all_sections:
        return f"📭 No memory sections for **{meta.project_name}**."

    lines = [
        f"🧠 **{meta.project_name}** — Memory Summary\n",
        f"- **ID**: `{meta.project_id}`",
        f"- **Path**: {meta.project_path}",
        f"- **Git Remote**: {meta.git_remote_url or 'N/A'}",
        f"- **Last Updated**: {meta.updated_at}\n",
        "| Section | Size | Last Updated |",
        "|---------|------|--------------|",
    ]

    empty_sections = []
    stale_sections = []
    large_sections = []
    needs_prune = False

    for s in all_sections:
        size = storage.get_section_size(meta.project_id, s)
        age = meta.section_age_days(s)
        staleness = _staleness_label(age)

        if size < 50:
            empty_sections.append(s)
            lines.append(f"| `{s}` | — | ⚠️ empty |")
        else:
            flag = ""
            if age is not None and age > STALE_WARNING_DAYS:
                stale_sections.append(s)
                flag = " ⏰"
            if size > LARGE_SECTION_CHARS:
                large_sections.append(s)
                flag += " 📦"
            if age is not None and age > PRUNE_SUGGESTION_DAYS:
                needs_prune = True
            lines.append(f"| `{s}` | {_format_size(size)} | {staleness}{flag} |")

    lines.append("")

    # --- Actionable warnings ---
    warnings = []

    if empty_sections:
        warnings.append(
            f"⚠️ **Empty sections**: {', '.join(f'`{s}`' for s in empty_sections)} — "
            f"fill these with `write_memory` to build project context."
        )

    if stale_sections:
        warnings.append(
            f"⏰ **Stale sections** (>{STALE_WARNING_DAYS} days): "
            f"{', '.join(f'`{s}`' for s in stale_sections)} — "
            f"review and update with current information."
        )

    if large_sections:
        warnings.append(
            f"📦 **Large sections** (>{_format_size(LARGE_SECTION_CHARS)} chars): "
            f"{', '.join(f'`{s}`' for s in large_sections)} — "
            f"consider pruning to keep context concise."
        )

    if needs_prune:
        warnings.append(
            f"🧹 **Some sections are over {PRUNE_SUGGESTION_DAYS} days old.** "
            f"Run `read_memory` with `prune=True` to review and clean up."
        )

    if warnings:
        lines.append("### Action Items\n")
        for w in warnings:
            lines.append(w)
        lines.append("")

    lines.append(
        '💡 Load sections: `read_memory(projectId, sections=["overview", "decisions"])`'
    )

    return "\n".join(lines)


def _selective_load(meta, sections: list[str], max_chars: int) -> str:
    """Load only the requested sections, with optional truncation."""
    invalid = [s for s in sections if not is_valid_section_name(s)]
    if invalid:
        return f"❌ Invalid section name(s): {invalid}."

    memory = storage.load_sections(meta.project_id, sections)
    if not memory:
        return f"📭 No content in requested sections: {', '.join(sections)}."

    parts = [f"# 🧠 {meta.project_name} — Selected Sections\n"]
    for sec, content in memory.items():
        staleness = _staleness_label(meta.section_age_days(sec))
        display = _truncate(content, max_chars) if max_chars > 0 else content
        parts.append(
            f"\n---\n## {sec.replace('_', ' ').title()} _{staleness}_\n\n{display}"
        )
    return "\n".join(parts)


def _search_mode(meta, query: str) -> str:
    """Search across all sections for a keyword."""
    results = storage.search_memory(meta.project_id, query)
    if not results:
        return f"🔍 No matches for `{query}` in **{meta.project_name}**."
    total = sum(len(v) for v in results.values())
    parts = [f"🔍 {total} match(es) for `{query}` in **{meta.project_name}**:\n"]
    for sec, snippets in results.items():
        parts.append(f"\n### {sec.replace('_', ' ').title()}\n")
        for snippet in snippets:
            parts.append(f"```\n{snippet}\n```")
    return "\n".join(parts)


def _history_mode(meta, section: str, limit: int) -> str:
    """Show previous snapshots of a section."""
    limit = max(1, min(limit, 5))
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


def _prune_mode(meta) -> str:
    """Load all sections with pruning instructions."""
    memory = storage.load_all_memory(meta.project_id)
    if not memory:
        return "📭 No memory to prune yet."
    parts = [
        f"# 🧹 Prune: {meta.project_name}\n",
        "Review each section and clean up:\n"
        "- Remove outdated information that no longer applies\n"
        "- Resolve contradictions (keep the newest version)\n"
        "- Remove duplicate entries\n"
        "- Condense verbose sections into concise summaries\n\n"
        "Then call `write_memory` with the cleaned content for any changed sections.\n",
    ]
    for sec, content in memory.items():
        staleness = _staleness_label(meta.section_age_days(sec))
        size = len(content)
        parts.append(
            f"\n---\n## {sec.replace('_', ' ').title()} _{staleness}_ ({_format_size(size)} chars)\n\n{content}"
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
    """Write to one or more memory sections. Call this to persist important project context.

    WHEN TO CALL THIS TOOL:
    - After making significant code changes (architecture, new features, refactors)
    - When important decisions are made (tech choices, design patterns, trade-offs)
    - When work context changes (switching tasks, starting new features)
    - At the end of a productive session to capture progress
    - When the user asks you to "remember" or "save" something

    Modes:

      append=False (default) — overwrite sections with full new content.
        Always provide the complete current state, not just a diff.
        Previous content is auto-saved to history before overwriting.

      append=True — add a timestamped entry to the bottom of each section.
        Use for incremental updates: new decisions, progress notes, issues.
        Existing content is preserved — no need to read first.
        `heading` sets an optional heading for the appended entry.

    Default sections: overview, decisions, active_context, progress.
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
# TOOL 4 — manage_projects
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
# MCP PROMPTS — Agent workflow templates
# ===========================================================================

@mcp.prompt()
def start_session(projectPath: str) -> str:
    """Standard workflow for the START of every conversation.

    Call this prompt at the beginning of each session to properly
    initialize project context and load relevant memory.
    """
    return f"""You are working on a project. Follow these steps to initialize your context:

1. **Initialize the project** by calling:
   `init_project(projectPath="{projectPath}")`

2. **Read the memory summary** (returned by init_project). Look at:
   - Which sections have content vs. are empty
   - Which sections are stale (⏰) and may need updating
   - Any action items listed

3. **Load relevant sections** based on the current task:
   - For general context: `read_memory(projectId, sections=["overview", "active_context"])`
   - For architecture work: `read_memory(projectId, sections=["overview", "decisions"])`
   - For progress updates: `read_memory(projectId, sections=["active_context", "progress"])`

4. **Update stale sections** if any are flagged:
   - Review the stale content
   - Update with current information using `write_memory`

5. **Before ending the conversation**, update memory with any important changes:
   - New decisions → append to `decisions`
   - Changed work focus → update `active_context`
   - Completed tasks → update `progress`

This ensures your project knowledge persists across IDEs and conversations."""


@mcp.prompt()
def bootstrap_memory(projectPath: str) -> str:
    """Guided workflow to populate memory for a project that has no existing memory.

    Use this when adopting IDE Memory for an existing project, or when
    a user asks you to "learn about this project" or "remember this project".
    """
    return f"""This project needs its memory populated. Analyze the project at `{projectPath}` and create comprehensive memory.

**Step 1: Analyze the project**
Look at these files to understand the project:
- README.md, README, or similar documentation
- Package files: package.json, pyproject.toml, Cargo.toml, go.mod, pom.xml, etc.
- Configuration files: .env.example, docker-compose.yml, Makefile, etc.
- Entry points: src/, app/, main files
- Test structure: tests/, __tests__/, spec/

**Step 2: Write the overview**
Call `write_memory` with a comprehensive overview section:
```
write_memory(projectId, {{
  "overview": "# Project Overview\\n\\n## What It Does\\n[describe purpose]\\n\\n## Tech Stack\\n[list technologies]\\n\\n## Architecture\\n[describe high-level architecture]\\n\\n## Key Files\\n[list important files and their roles]"
}})
```

**Step 3: Document decisions**
Record any architectural decisions you can infer:
```
write_memory(projectId, {{
  "decisions": "# Technical Decisions\\n\\n## [Decision 1]\\n- **Choice**: [what was chosen]\\n- **Rationale**: [why]\\n- **Alternatives considered**: [what else was considered]"
}})
```

**Step 4: Set active context**
Document what appears to be the current state of work:
```
write_memory(projectId, {{
  "active_context": "# Active Context\\n\\n## Current State\\n[what state the project is in]\\n\\n## Recent Changes\\n[any recent changes visible in git or file timestamps]\\n\\n## Open Issues\\n[any TODOs or FIXMEs found in code]"
}})
```

**Step 5: Record progress**
Document the project's current progress:
```
write_memory(projectId, {{
  "progress": "# Progress\\n\\n## Completed\\n[what's built and working]\\n\\n## In Progress\\n[what's currently being worked on]\\n\\n## Planned\\n[what's next]"
}})
```

After completing all steps, the project memory will persist across all IDEs and future conversations."""


@mcp.prompt()
def update_memory(projectIdOrPath: str) -> str:
    """Workflow to review and update memory after making significant changes.

    Use this at the end of a session, after major refactors, or when
    the user asks you to "update the memory" or "save what we did".
    """
    return f"""Review what was accomplished in this session and update the project memory.

**Step 1: Read current memory**
```
read_memory("{projectIdOrPath}", sections=["active_context", "decisions", "progress"])
```

**Step 2: Update active_context**
Replace with the current state of work:
- What was just completed
- What is currently in progress
- Any blockers or open questions
- What should be done next

**Step 3: Append new decisions** (if any were made)
For each significant technical decision made during this session:
```
write_memory("{projectIdOrPath}", {{
  "decisions": "[Decision description and rationale]"
}}, append=True, heading="[Decision Title]")
```

**Step 4: Update progress**
Add completed items and any new planned work:
```
write_memory("{projectIdOrPath}", {{
  "progress": "[What was accomplished, what's next]"
}}, append=True, heading="Session Update")
```

**Step 5: Update overview** (if needed)
If the tech stack, architecture, or project scope changed, update the overview:
```
read_memory("{projectIdOrPath}", sections=["overview"])
```
Then rewrite with updated information.

**Step 6: Check for pruning**
If memory has grown large or has old entries, consider running:
```
read_memory("{projectIdOrPath}", prune=True)
```
And clean up any outdated information."""


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