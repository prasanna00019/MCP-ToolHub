"""
IDE Memory MCP — CLI utilities.

Practical commands that make the pip package genuinely useful:
  ide-memory-mcp setup    — auto-configure MCP for your IDEs
  ide-memory-mcp doctor   — health check the installation
  ide-memory-mcp status   — show registered projects and memory stats

When called with no subcommand, starts the MCP server (backward compatible).
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
from pathlib import Path

from ide_memory_mcp.storage import MemoryStorage


# ---------------------------------------------------------------------------
# IDE config path detection
# ---------------------------------------------------------------------------

def _home() -> Path:
    return Path.home()


def _ide_config_paths() -> dict[str, Path | None]:
    """Return config file paths for each supported IDE, None if not applicable."""
    home = _home()
    system = platform.system()

    paths: dict[str, Path | None] = {}

    # Cursor — global MCP config
    cursor_dir = home / ".cursor"
    paths["cursor"] = cursor_dir / "mcp.json" if cursor_dir.exists() else cursor_dir / "mcp.json"

    # VS Code — global settings (user-level)
    if system == "Windows":
        vscode_dir = Path(os.environ.get("APPDATA", "")) / "Code" / "User"
    elif system == "Darwin":
        vscode_dir = home / "Library" / "Application Support" / "Code" / "User"
    else:
        vscode_dir = home / ".config" / "Code" / "User"
    paths["vscode"] = vscode_dir / "mcp.json"

    # Windsurf
    paths["windsurf"] = home / ".codeium" / "windsurf" / "mcp_config.json"

    # Claude Desktop
    if system == "Windows":
        claude_dir = Path(os.environ.get("APPDATA", "")) / "Claude"
    elif system == "Darwin":
        claude_dir = home / "Library" / "Application Support" / "Claude"
    else:
        claude_dir = home / ".config" / "Claude"
    paths["claude"] = claude_dir / "claude_desktop_config.json"

    # Antigravity
    paths["antigravity"] = home / ".gemini" / "antigravity" / "mcp_config.json"

    return paths


def _mcp_server_entry() -> dict:
    """Return the MCP server config block for ide-memory."""
    return {
        "command": "ide-memory-mcp",
    }


def _merge_mcp_config(config_path: Path, server_key: str = "ide-memory", root_key: str = "mcpServers") -> bool:
    """Merge ide-memory MCP config into an existing config file.

    Returns True if the file was created/updated, False if already configured.
    """
    existing = {}
    if config_path.exists():
        try:
            existing = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = {}

    # Ensure root key exists
    if root_key not in existing:
        existing[root_key] = {}

    # Check if already configured
    if server_key in existing[root_key]:
        current = existing[root_key][server_key]
        if isinstance(current, dict) and current.get("command") == "ide-memory-mcp":
            return False  # Already configured

    # Add/update
    existing[root_key][server_key] = _mcp_server_entry()

    # Write
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(existing, indent=2) + "\n",
        encoding="utf-8",
    )
    return True


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

IDE_LABELS = {
    "cursor": "Cursor",
    "vscode": "VS Code",
    "windsurf": "Windsurf",
    "claude": "Claude Desktop",
    "antigravity": "Antigravity",
}


def cmd_setup(args: argparse.Namespace) -> None:
    """Auto-configure MCP for IDEs."""
    ide_paths = _ide_config_paths()

    # Determine which IDEs to configure
    selected = []
    if args.all:
        selected = list(ide_paths.keys())
    else:
        for ide in ide_paths:
            if getattr(args, ide, False):
                selected.append(ide)

    if not selected:
        # Auto-detect: configure IDEs whose parent directories exist
        for ide, path in ide_paths.items():
            if path and path.parent.exists():
                selected.append(ide)

        if not selected:
            print("No IDEs detected. Use --all or specify an IDE:")
            for ide, label in IDE_LABELS.items():
                print(f"  --{ide:10s}  Configure {label}")
            return

        print(f"Auto-detected {len(selected)} IDE(s). Configuring...\n")

    configured = 0
    skipped = 0
    for ide in selected:
        path = ide_paths.get(ide)
        label = IDE_LABELS.get(ide, ide)
        if not path:
            continue

        try:
            root_key = "servers" if ide == "vscode" else "mcpServers"
            updated = _merge_mcp_config(path, root_key=root_key)
            if updated:
                print(f"  ✅ {label:16s} → {path}")
                configured += 1
            else:
                print(f"  ⏭️  {label:16s} → already configured")
                skipped += 1
        except OSError as e:
            print(f"  ❌ {label:16s} → error: {e}")

    print(f"\nDone! {configured} configured, {skipped} already set up.")
    if configured > 0:
        print("\n💡 Restart your IDE(s) to activate the MCP server.")


def cmd_doctor(args: argparse.Namespace) -> None:
    """Health check the installation."""
    print("🩺 IDE Memory MCP — Health Check\n")

    # 1. Server import check
    try:
        from ide_memory_mcp.server import mcp  # noqa: F401
        print("  ✅ Server module loads correctly")
    except Exception as e:
        print(f"  ❌ Server import error: {e}")
        return

    # 2. Storage location
    storage = MemoryStorage()
    print(f"  📁 Storage: {storage.root}")
    if storage.root.exists():
        # Count files and size
        total_size = sum(f.stat().st_size for f in storage.root.rglob("*") if f.is_file())
        if total_size < 1024:
            size_str = f"{total_size} bytes"
        elif total_size < 1024 * 1024:
            size_str = f"{total_size / 1024:.1f} KB"
        else:
            size_str = f"{total_size / (1024 * 1024):.1f} MB"
        print(f"     Disk usage: {size_str}")
    else:
        print("     (not yet created — will be created on first use)")

    # 3. Projects
    projects = storage.list_projects()
    print(f"  📋 Projects: {len(projects)} registered")

    # 4. IDE configurations
    print("\n  IDE Configurations:")
    ide_paths = _ide_config_paths()
    any_configured = False
    for ide, path in ide_paths.items():
        label = IDE_LABELS.get(ide, ide)
        if path and path.exists():
            try:
                config = json.loads(path.read_text(encoding="utf-8"))
                servers = config.get("mcpServers", {})
                if "ide-memory" in servers:
                    print(f"    ✅ {label} — configured")
                    any_configured = True
                else:
                    print(f"    ⚠️  {label} — config exists but ide-memory not added")
            except (json.JSONDecodeError, OSError):
                print(f"    ⚠️  {label} — config file exists but couldn't be read")
        else:
            print(f"    —  {label} — not configured")

    if not any_configured:
        print("\n  💡 Run `ide-memory-mcp setup` to auto-configure your IDEs.")

    # 5. Command availability
    print(f"\n  🔧 Command: {shutil.which('ide-memory-mcp') or 'not found in PATH'}")
    print(f"  🐍 Python: {sys.version.split()[0]}")


def cmd_status(args: argparse.Namespace) -> None:
    """Show registered projects and memory stats."""
    storage = MemoryStorage()
    projects = storage.list_projects()

    if not projects:
        print("📭 No projects registered yet.")
        print("   Use your IDE's AI agent to call `init_project` and get started.")
        return

    print(f"📋 {len(projects)} registered project(s)\n")
    print(f"{'Project':<30s} {'Sections':<10s} {'Size':<10s} {'Last Updated'}")
    print(f"{'─' * 30}  {'─' * 8}  {'─' * 8}  {'─' * 20}")

    for p in sorted(projects, key=lambda x: x.updated_at, reverse=True):
        sections = storage.get_all_section_names(p.project_id)
        non_empty = 0
        total_size = 0
        for s in sections:
            size = storage.get_section_size(p.project_id, s)
            if size > 50:
                non_empty += 1
            total_size += size

        # Format size
        if total_size < 1000:
            size_str = f"{total_size} B"
        elif total_size < 10_000:
            size_str = f"{total_size / 1000:.1f} KB"
        else:
            size_str = f"{total_size // 1000} KB"

        name = p.project_name[:28]
        sec_str = f"{non_empty}/{len(sections)}"
        updated = p.updated_at[:10] if p.updated_at else "never"

        print(f"  {name:<28s} {sec_str:<10s} {size_str:<10s} {updated}")

    print(f"\n📁 Storage: {storage.root}")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Main CLI entry point. Dispatches subcommands or starts the MCP server."""
    # Quick check: if no args or first arg looks like it's not a subcommand,
    # start the server directly (backward compatible)
    if len(sys.argv) <= 1:
        _start_server()
        return

    # Check if the first argument is a known subcommand
    subcommands = {"setup", "doctor", "status"}
    if sys.argv[1] not in subcommands and not sys.argv[1].startswith("-"):
        _start_server()
        return

    parser = argparse.ArgumentParser(
        prog="ide-memory-mcp",
        description="IDE Memory MCP — Cross-IDE persistent memory for AI coding agents",
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # --- setup ---
    setup_parser = sub.add_parser(
        "setup",
        help="Auto-configure MCP for your IDEs",
        description="Detect installed IDEs and configure them to use IDE Memory MCP.",
    )
    setup_parser.add_argument("--cursor", action="store_true", help="Configure Cursor")
    setup_parser.add_argument("--vscode", action="store_true", help="Configure VS Code")
    setup_parser.add_argument("--windsurf", action="store_true", help="Configure Windsurf")
    setup_parser.add_argument("--claude", action="store_true", help="Configure Claude Desktop")
    setup_parser.add_argument("--antigravity", action="store_true", help="Configure Antigravity")
    setup_parser.add_argument("--all", action="store_true", help="Configure all supported IDEs")

    # --- doctor ---
    sub.add_parser(
        "doctor",
        help="Health check the installation",
        description="Verify server, storage, and IDE configurations.",
    )

    # --- status ---
    sub.add_parser(
        "status",
        help="Show registered projects and memory stats",
        description="List all projects with section count, size, and last update.",
    )

    args = parser.parse_args()

    if args.command == "setup":
        cmd_setup(args)
    elif args.command == "doctor":
        cmd_doctor(args)
    elif args.command == "status":
        cmd_status(args)
    else:
        parser.print_help()


def _start_server() -> None:
    """Start the MCP server (delegates to server.main)."""
    from ide_memory_mcp.server import main as server_main
    server_main()


if __name__ == "__main__":
    main()
