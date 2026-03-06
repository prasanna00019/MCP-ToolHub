"""
IDE Memory MCP Server — Entry point.

A cross-IDE persistent memory layer for AI coding agents.
Run with: uv run ide-memory-mcp
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from ide_memory_mcp.storage import MemoryStorage, scan_directory_tree
from ide_memory_mcp.models import MEMORY_SECTIONS

# ---------------------------------------------------------------------------
# Logging (to stderr so we don't corrupt JSON-RPC on stdout)
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("ide-memory-mcp")

# ---------------------------------------------------------------------------
# Module-level FastMCP server & storage
# ---------------------------------------------------------------------------
mcp = FastMCP("ide-memory-mcp")
storage = MemoryStorage()


# ===========================================================================
# TOOLS
# ===========================================================================

@mcp.tool()
async def init_project(
    projectPath: str,
    projectName: str = "",
    gitRemoteUrl: str = "",
) -> str:
    """Register or reconnect to a project for memory tracking.

    If the project already exists (matched by path or git remote),
    returns existing memory. Otherwise creates a new project entry.
    """
    meta, is_new = storage.init_project(
        projectPath,
        projectName or None,
        gitRemoteUrl or None,
    )

    if is_new:
        return (
            f"✅ New project registered!\n\n"
            f"- **Project ID**: `{meta.project_id}`\n"
            f"- **Name**: {meta.project_name}\n"
            f"- **Path**: {meta.project_path}\n"
            f"- **Git Remote**: {meta.git_remote_url or 'N/A'}\n\n"
            f"Memory sections created: {', '.join(MEMORY_SECTIONS)}\n\n"
            f"⚡ **ACTION REQUIRED**: This project has empty memory. "\
            f"You MUST now do the following:\n"\
            f"1. Call `scan_project_structure` with this project ID to auto-capture the directory tree\n"\
            f"2. Call `update_memory` to fill in the remaining sections:\n"\
            f"- `overview`: project purpose, tech stack, architecture\n"\
            f"- `decisions`: architectural decisions and rationale\n"\
            f"- `active_context`: current work, recent changes\n"\
            f"- `progress`: completed milestones, TODOs, known issues\n\n"\
            f"🔄 **ONGOING**: After every significant change you make to this project, "\
            f"call `update_memory` to keep the memory in sync."
        )

    # Existing project — show summary
    memory = storage.load_all_memory(meta.project_id)
    section_summary = ", ".join(f"{k} ({len(v)} chars)" for k, v in memory.items())

    # Check if any sections are essentially empty (just the header)
    empty_sections = [
        s for s in MEMORY_SECTIONS
        if len(storage.get_section(meta.project_id, s).strip()) < 50
    ]
    empty_hint = ""
    if empty_sections:
        empty_hint = (
            f"\n\n⚡ **ACTION REQUIRED**: The following sections are empty or sparse: "
            f"{', '.join(empty_sections)}. "
            f"Please analyze the project and fill these in using `update_memory`."
        )

    return (
        f"🔗 Reconnected to existing project!\n\n"
        f"- **Project ID**: `{meta.project_id}`\n"
        f"- **Name**: {meta.project_name}\n"
        f"- **Path**: {meta.project_path}\n"
        f"- **Git Remote**: {meta.git_remote_url or 'N/A'}\n"
        f"- **Last Updated**: {meta.updated_at}\n\n"
        f"**Memory sections**: {section_summary}\n\n"
        f"Use `load_memory` to read full project memory."
        f"{empty_hint}\n\n"
        f"🔄 **ONGOING**: After every significant change you make to this project, "
        f"call `update_memory` to keep the memory in sync."
    )


@mcp.tool()
async def load_memory(projectIdOrPath: str) -> str:
    """Load all memory sections for a project.

    Returns the full project memory as structured markdown.
    Accepts project ID or absolute project path.
    """
    meta = storage.resolve_project(projectIdOrPath)
    if not meta:
        return f"❌ Project `{projectIdOrPath}` not found."

    memory = storage.load_all_memory(meta.project_id)
    if not memory:
        return "📭 No memory stored yet. Use `update_memory` to add context."

    parts = [f"# 🧠 Project Memory: {meta.project_name}\n"]
    for section, content in memory.items():
        parts.append(f"\n---\n## {section.replace('_', ' ').title()}\n\n{content}")

    return "\n".join(parts)


@mcp.tool()
async def update_memory(projectIdOrPath: str, sections: dict[str, str]) -> str:
    """Update one or more memory sections for a project.

    Provide section names as keys and full new content as values.
    Valid sections: overview, structure, decisions, active_context, progress.
    Accepts project ID or absolute project path.

    IMPORTANT: Call this tool after every significant change you make to the project.
    Always provide the FULL current state of each section, not just the diff.
    """
    meta = storage.resolve_project(projectIdOrPath)
    if not meta:
        return f"❌ Project `{projectIdOrPath}` not found."

    invalid = [s for s in sections if s not in MEMORY_SECTIONS]
    if invalid:
        return f"❌ Invalid sections: {invalid}. Valid: {MEMORY_SECTIONS}"

    updated = storage.update_multiple_sections(meta.project_id, sections)

    # Check what's still empty after update
    still_empty = [
        s for s in MEMORY_SECTIONS
        if s not in sections and len(storage.get_section(meta.project_id, s).strip()) < 50
    ]
    reminder = ""
    if still_empty:
        reminder = (
            f"\n\n💡 These sections are still empty: {', '.join(still_empty)}. "
            f"Consider filling them in too."
        )

    return (
        f"✅ Updated {len(updated)} section(s): {', '.join(updated)}"
        f"{reminder}\n\n"
        f"🔄 Remember: call `update_memory` again after your next significant change."
    )


@mcp.tool()
async def get_memory_section(projectIdOrPath: str, section: str) -> str:
    """Get a specific memory section for a project.

    Valid sections: overview, structure, decisions, active_context, progress.
    Accepts project ID or absolute project path.
    """
    meta = storage.resolve_project(projectIdOrPath)
    if not meta:
        return f"❌ Project `{projectIdOrPath}` not found."

    if section not in MEMORY_SECTIONS:
        return f"❌ Invalid section: {section}. Valid: {MEMORY_SECTIONS}"

    content = storage.get_section(meta.project_id, section)
    if not content.strip():
        return f"📭 Section `{section}` is empty."

    return content


@mcp.tool()
async def list_projects() -> str:
    """List all known projects with their names, paths, and last-active timestamps."""
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


@mcp.tool()
async def scan_project_structure(
    projectIdOrPath: str,
    maxDepth: int = 4,
    maxFiles: int = 200,
) -> str:
    """Automatically scan the project directory and save the file tree to the 'structure' memory section.

    This reads the actual directory tree (respecting .gitignore-like patterns)
    and saves a formatted tree view.
    Accepts project ID or absolute project path.
    """
    meta = storage.resolve_project(projectIdOrPath)
    if not meta:
        return f"❌ Project `{projectIdOrPath}` not found."

    # Scan the directory
    tree = scan_directory_tree(meta.project_path, max_depth=maxDepth, max_files=maxFiles)

    # Save to structure section
    storage.update_section(meta.project_id, "structure", tree)

    return (
        f"✅ Scanned and saved project structure for **{meta.project_name}**\n\n"
        f"{tree}\n\n"
        f"💡 This has been saved to the `structure` memory section. "
        f"The agent can enrich it further with descriptions of key files using `update_memory`."
    )


@mcp.tool()
async def prune_memory(projectIdOrPath: str) -> str:
    """Load all memory sections so the agent can prune them.

    Returns all memory sections as markdown. The agent should then:
    1. Read each section carefully.
    2. Remove outdated, contradicted, or duplicate content.
    3. Call `update_memory` with the cleaned versions.

    Accepts project ID or absolute project path.
    """
    meta = storage.resolve_project(projectIdOrPath)
    if not meta:
        return f"❌ Project `{projectIdOrPath}` not found."

    memory = storage.load_all_memory(meta.project_id)
    if not memory:
        return "📭 No memory to prune yet."

    parts = [f"# 🧹 Prune Task: {meta.project_name}\n"]
    parts.append(
        "**Instructions for the agent**: Review each section below and remove:\n"
        "- Outdated or superceded information\n"
        "- Contradictions (keep the most recent state)\n"
        "- Duplicate or redundant entries\n\n"
        "After pruning, call `update_memory` with the cleaned content for each section that changed.\n"
    )
    for section, content in memory.items():
        parts.append(f"\n---\n## {section.replace('_', ' ').title()}\n\n{content}")

    return "\n".join(parts)


# ===========================================================================
# RESOURCES
# ===========================================================================

@mcp.resource("memory://{project_id}/{section}")
async def read_memory_resource(project_id: str, section: str) -> str:
    """Read a project memory section as a resource."""
    if section not in MEMORY_SECTIONS:
        raise ValueError(f"Unknown section: {section}. Valid: {MEMORY_SECTIONS}")
    return storage.get_section(project_id, section)


# ===========================================================================
# Entry point
# ===========================================================================

def main() -> None:
    """Main entry point — start the MCP server over stdio."""
    logger.info("IDE Memory MCP server starting...")
    logger.info("Memory root: %s", storage.root)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
