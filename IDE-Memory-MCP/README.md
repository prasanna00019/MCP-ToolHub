# IDE Memory MCP

<p align="center">
  <img src="logo.png" alt="IDE Memory MCP" width="200"/>
</p>

> **Cross-IDE persistent memory for AI coding agents** — your AI remembers every project, across every IDE.

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/protocol-MCP-purple.svg)](https://modelcontextprotocol.io/)

---

## The Problem

Every time you open a project in a new IDE or start a fresh AI conversation, your AI assistant forgets everything:

- What the project does
- Architecture decisions you've made
- What you're currently working on
- Your progress and milestones

You end up repeating yourself. Every. Single. Time.

## The Solution

**IDE Memory MCP** gives AI coding agents a **persistent memory layer** that works across any IDE supporting the [Model Context Protocol](https://modelcontextprotocol.io/). Write project context once — the AI remembers it everywhere.

```
Cursor ←──→ IDE Memory MCP ←──→ VS Code
   ↑              ↓                 ↑
   └── same project memory ────────┘
```

---

## Key Features

- **Cross-IDE Memory** — Project context persists across Cursor, VS Code, Windsurf, Claude Desktop, and any MCP-compatible IDE
- **Context-Optimized** — Default reads return a compact summary table, not a context-window-destroying content dump. The AI loads only what it needs.
- **Smart Warnings** — Automatically detects stale sections (>7 days), oversized content (>10k chars), and suggests pruning when memory gets old (>30 days)
- **Agent Prompts** — Built-in MCP prompts guide the AI on how to start sessions, bootstrap memory for new projects, and update memory after changes
- **Smart Project Matching** — Recognizes projects by path or git remote URL. Move folders, switch machines — your memory follows.
- **Section-Based Storage** — Organized into `overview`, `decisions`, `active_context`, `progress` + custom sections
- **Append Mode** — Add incremental updates without rewriting entire sections
- **Version History** — Previous content auto-saved before each overwrite (last 5 snapshots)
- **Zero Config** — Works out of the box. No database, no cloud, just local markdown files.

---

## Quick Start

### Install

```bash
# Using uv (recommended)
uv pip install ide-memory-mcp

# Using pip
pip install ide-memory-mcp
```

### From Source (Development)

```bash
git clone https://github.com/prasanna-pmpeople/IDE-Memory-MCP.git
cd IDE-Memory-MCP
uv sync
```

### Configure Your IDE

Add the MCP server to your IDE's configuration:

<details>
<summary><b>Cursor</b> — <code>.cursor/mcp.json</code></summary>

```json
{
  "mcpServers": {
    "ide-memory": {
      "command": "ide-memory-mcp"
    }
  }
}
```

If installed from source:
```json
{
  "mcpServers": {
    "ide-memory": {
      "command": "uv",
      "args": ["--directory", "/path/to/IDE-Memory-MCP", "run", "ide-memory-mcp"]
    }
  }
}
```

</details>

<details>
<summary><b>VS Code</b> — <code>.vscode/mcp.json</code></summary>

```json
{
  "mcpServers": {
    "ide-memory": {
      "command": "ide-memory-mcp"
    }
  }
}
```

</details>

<details>
<summary><b>Windsurf</b> — <code>~/.codeium/windsurf/mcp_config.json</code></summary>

```json
{
  "mcpServers": {
    "ide-memory": {
      "command": "ide-memory-mcp"
    }
  }
}
```

</details>

<details>
<summary><b>Claude Desktop</b> — <code>claude_desktop_config.json</code></summary>

```json
{
  "mcpServers": {
    "ide-memory": {
      "command": "ide-memory-mcp"
    }
  }
}
```

Config location:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

</details>

Restart your IDE after adding the configuration.

---

## Tools

IDE Memory MCP exposes **4 optimized tools** to the AI agent:

### `init_project`

Register or reconnect to a project. **Call this first** in every conversation.

```
init_project(projectPath, projectName?, gitRemoteUrl?)
```

- New project → creates memory storage, suggests next steps, mentions `bootstrap_memory` prompt
- Known project → reconnects, returns memory summary with **smart warnings**:
  - ⚠️ Empty sections that need filling
  - ⏰ Stale sections (>7 days) that should be updated
  - 📦 Large sections (>10k chars) that may need pruning
  - 🧹 Old sections (>30 days) suggesting a full prune

### `read_memory`

Context-aware memory loading. **Optimized to avoid flooding the AI's context window.**

```
read_memory(projectIdOrPath, sections?, query?, maxChars?, history?, prune?)
```

| Mode | Trigger | What it does |
|------|---------|-------------|
| **Summary** (default) | No `sections` | Returns a compact table: section names, sizes, staleness, warnings. **No content.** |
| **Selective** | `sections=["overview"]` | Loads only the listed sections |
| **Truncated** | `maxChars=500` | Caps each section at N characters |
| **Search** | `query="auth"` | Keyword search across all sections |
| **History** | `history=True` | Shows previous versions of a section |
| **Prune** | `prune=True` | Loads all with actionable cleanup instructions |

**💡 Recommended workflow:**
1. `read_memory(projectId)` → get the summary table (~10 lines)
2. Decide which sections are relevant
3. `read_memory(projectId, sections=["overview", "decisions"])` → load only what you need

### `write_memory`

Write to one or more memory sections.

```
write_memory(projectIdOrPath, sections, append?, heading?)
```

- **Overwrite mode** (default): Replace entire section content. Previous content auto-saved to history.
- **Append mode** (`append=True`): Add timestamped entries without rewriting. Great for decisions and progress logs.

Tool description includes **behavioral guidance** — it tells the AI agent *when* to call it:
- After significant code changes
- When important decisions are made
- At the end of productive sessions
- When the user asks to "remember" something

### `manage_projects`

List or delete projects.

```
manage_projects(action, projectIdOrPath?, confirm?)
```

---

## MCP Prompts

IDE Memory MCP includes **3 built-in prompt templates** that guide the AI agent through common workflows. These solve the "agent doesn't know when to use memory" problem.

### `start_session`

**When:** Beginning of every conversation.

Guides the agent through: initialize project → read summary → load relevant sections → check for stale content → plan memory updates for end of session.

### `bootstrap_memory`

**When:** First time using IDE Memory on an existing project, or when the user says *"learn about this project"*.

Guides the agent through: analyze README & package files → write comprehensive overview → document architecture decisions → set active context → record progress.

### `update_memory`

**When:** End of a productive session, after significant changes, or when the user says *"save what we did"*.

Guides the agent through: read current memory → update active_context → append new decisions → update progress → update overview if needed → check if pruning is needed.

---

## Memory Sections

Default sections created for every project:

| Section | Purpose |
|---------|---------|
| `overview` | What the project is, tech stack, architecture |
| `decisions` | Key technical decisions and rationale |
| `active_context` | What you're currently working on |
| `progress` | Milestones, completed items, what's next |

**Custom sections** are fully supported — use any lowercase identifier:

```
write_memory(projectId, {"api_contracts": "...", "testing_notes": "..."})
```

---

## Smart Warnings

The memory summary automatically includes actionable warnings:

| Warning | Trigger | Action |
|---------|---------|--------|
| ⚠️ Empty | Section has <50 chars | Fill with `write_memory` |
| ⏰ Stale | Section not updated in >7 days | Review and update |
| 📦 Large | Section exceeds 10k chars | Consider pruning |
| 🧹 Prune | Any section >30 days old | Run `read_memory(prune=True)` |

---

## Storage

All memory is stored as simple markdown files in `~/.ide-memory/projects/`:

```
~/.ide-memory/
├── config.json              # Optional configuration
└── projects/
    └── <project_id>/
        ├── meta.json         # Project metadata + timestamps
        ├── overview.md
        ├── decisions.md
        ├── active_context.md
        ├── progress.md
        └── .history/         # Auto-saved snapshots
            ├── overview_20260314_120000.md
            └── decisions_20260314_130000.md
```

- No database required
- All files are human-readable markdown
- Easy to backup, version, or migrate
- No data ever leaves your machine

---

## Configuration

Optional. Create `~/.ide-memory/config.json`:

```json
{
  "default_sections": [
    "overview",
    "decisions",
    "active_context",
    "progress"
  ]
}
```

---

## Development

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Setup

```bash
git clone https://github.com/prasanna-pmpeople/IDE-Memory-MCP.git
cd IDE-Memory-MCP
uv sync
```

### Run the server

```bash
uv run ide-memory-mcp
```

### Run tests

```bash
uv run pytest tests/ -v
```

### Test with MCP Inspector

```bash
npx -y @modelcontextprotocol/inspector uv run ide-memory-mcp
```

See [TESTING.md](TESTING.md) for the complete testing guide, including MCP Inspector walkthrough and cross-IDE battle testing.

### Build the package

```bash
uv build
```

### Install from built package

```bash
pip install dist/ide_memory_mcp-0.2.0-py3-none-any.whl
```

---

## How It Works

```mermaid
sequenceDiagram
    participant Agent as AI Agent (any IDE)
    participant MCP as IDE Memory MCP
    participant FS as ~/.ide-memory/

    Note over Agent,FS: Session Start
    Agent->>MCP: init_project(path)
    MCP->>FS: Check for existing project
    FS-->>MCP: Found (reconnect)
    MCP-->>Agent: Summary table + smart warnings

    Agent->>MCP: read_memory(id, sections=["overview"])
    MCP->>FS: Read only overview.md
    MCP-->>Agent: Overview content

    Note over Agent,FS: During Session
    Agent->>MCP: write_memory(id, {decisions: "..."}, append=True)
    MCP->>FS: Save to history → append decisions.md
    MCP-->>Agent: ✅ Appended

    Note over Agent,FS: Session End
    Agent->>MCP: write_memory(id, {active_context: "...", progress: "..."})
    MCP->>FS: Save to history → update sections
    MCP-->>Agent: ✅ Updated — memory persists for next session
```

---

## License

MIT — see [LICENSE](LICENSE) for details.
