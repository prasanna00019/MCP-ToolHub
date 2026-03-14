# Testing IDE Memory MCP

This guide covers how to thoroughly test the IDE Memory MCP server — from unit tests to battle-testing across real IDEs.

---

## 1. Unit Tests (pytest)

Run the full test suite:

```bash
cd IDE-Memory-MCP
uv run pytest tests/ -v
```

Run with coverage:

```bash
uv run pytest tests/ -v --cov=ide_memory_mcp --cov-report=term-missing
```

### What the tests cover (35 tests)

| Test file | Tests | Coverage |
|-----------|-------|----------|
| `test_storage.py` | 15 | Path normalization, git URL normalization, section name validation, project CRUD, section read/write, selective loading, search, history, custom sections, delete, list |
| `test_server.py` — Tools | 18 | All 4 MCP tools end-to-end: `init_project` (new + reconnect + bootstrap mention + empty warning), `read_memory` (summary, selective, maxChars, search, stale detection, prune instructions), `write_memory` (overwrite + append + empty reminder), `manage_projects` (list + delete) |
| `test_server.py` — Prompts | 3 | All 3 MCP prompts return correct content: `start_session`, `bootstrap_memory`, `update_memory` |

---

## 2. MCP Inspector Testing

The [MCP Inspector](https://github.com/modelcontextprotocol/inspector) is the best way to interactively test MCP tools and prompts.

### Start the inspector

```bash
npx -y @modelcontextprotocol/inspector uv run ide-memory-mcp
```

Opens a web UI at `http://localhost:6274`.

### Step 1: Verify tools & prompts exposed

In the Inspector UI:
- **Tools** → should show exactly 4: `init_project`, `read_memory`, `write_memory`, `manage_projects`
- **Prompts** → should show exactly 3: `start_session`, `bootstrap_memory`, `update_memory`

### Step 2: Test `init_project` — new project

```json
{
  "projectPath": "C:/Users/you/projects/my-test-app",
  "projectName": "My Test App"
}
```

✅ Expected:
- "New project registered!"
- Mentions `bootstrap_memory` prompt
- Lists all 4 default sections with descriptions

### Step 3: Test `read_memory` — summary mode (DEFAULT)

```json
{
  "projectIdOrPath": "<project_id>"
}
```

✅ Expected:
- Compact summary **table** with section names, sizes, staleness
- **Action Items** section warning about empty sections
- Should NOT contain any actual section content

### Step 4: Test `write_memory` — populate sections

```json
{
  "projectIdOrPath": "<project_id>",
  "sections": {
    "overview": "# My Test App\n\nA React + Node.js e-commerce platform.\n\n## Tech Stack\n- Frontend: React 18, TypeScript\n- Backend: Node.js, Express\n- Database: PostgreSQL\n- Cache: Redis",
    "decisions": "# Decisions\n\n## Auth: JWT + Refresh Tokens\nChose JWT over sessions for stateless API.\n\n## Database: PostgreSQL over MongoDB\nRelational data model fits our product catalog."
  }
}
```

✅ Expected: "Updated 2 section(s)" with reminder about still-empty sections.

### Step 5: Test `read_memory` — summary with mixed state

Call `read_memory` again (no sections). Summary should now show:
- `overview` and `decisions` with sizes and "updated today"
- `active_context` and `progress` as "⚠️ empty"
- Action Items warning about empty sections

### Step 6: Test `read_memory` — selective load

```json
{
  "projectIdOrPath": "<project_id>",
  "sections": ["overview"]
}
```

✅ Expected: Only overview content returned. No decisions.

### Step 7: Test `read_memory` — maxChars truncation

```json
{
  "projectIdOrPath": "<project_id>",
  "sections": ["overview"],
  "maxChars": 50
}
```

✅ Expected: Truncated overview with "... (truncated — showing X of Y chars)".

### Step 8: Test `read_memory` — search

```json
{
  "projectIdOrPath": "<project_id>",
  "query": "PostgreSQL"
}
```

✅ Expected: Matches found in both `overview` and `decisions`.

### Step 9: Test `write_memory` — append mode

```json
{
  "projectIdOrPath": "<project_id>",
  "sections": {
    "decisions": "Switched from REST to GraphQL for the product API."
  },
  "append": true,
  "heading": "API: GraphQL Migration"
}
```

✅ Expected: "Appended to 1 section(s)". Verify with selective read that both old and new content present.

### Step 10: Test `read_memory` — history

```json
{
  "projectIdOrPath": "<project_id>",
  "sections": ["decisions"],
  "history": true
}
```

✅ Expected: At least 1 snapshot.

### Step 11: Test `read_memory` — prune mode

```json
{
  "projectIdOrPath": "<project_id>",
  "prune": true
}
```

✅ Expected: All sections loaded with actionable cleanup instructions ("Remove outdated information...", etc.) and section sizes.

### Step 12: Test `init_project` — reconnect

```json
{
  "projectPath": "C:/Users/you/projects/my-test-app"
}
```

✅ Expected: Memory Summary table with smart warnings, NOT "New project registered".

### Step 13: Test MCP Prompts

In the Inspector, go to **Prompts**:

1. **`start_session`** — provide `projectPath` → should return step-by-step session initialization instructions
2. **`bootstrap_memory`** — provide `projectPath` → should return guided walkthrough for populating all sections
3. **`update_memory`** — provide `projectIdOrPath` → should return instructions for reviewing and updating memory

✅ Each prompt should mention `init_project`, `read_memory`, and `write_memory` with concrete examples.

### Step 14: Test `manage_projects` — list & delete

```json
{"action": "list"}
```
```json
{"action": "delete", "projectIdOrPath": "<project_id>"}
```
```json
{"action": "delete", "projectIdOrPath": "<project_id>", "confirm": true}
```

---

## 3. Cross-IDE Battle Testing

### Setup in each IDE

Follow the configuration in README.md for your IDE.

### Test Scenario: Full lifecycle across IDEs

1. **IDE A** (e.g., Cursor):
   - Open a real project
   - Ask: _"Initialize this project in IDE Memory and write an overview and key decisions"_
   - Verify: agent calls `init_project` → `write_memory`
   - Ask: _"Read the project memory"_ → verify summary table returned (not full dump)

2. **IDE B** (e.g., VS Code / Windsurf):
   - Open the **same project**
   - Ask: _"Check if this project has existing memory"_
   - Verify: agent reconnects, shows summary with content from IDE A
   - Ask: _"Load the overview and decisions"_ → verify exact content from IDE A
   - Make some changes → ask: _"Update the memory with what we did"_

3. **Back to IDE A**:
   - Ask: _"Read the progress section"_
   - Verify: updates from IDE B are present

### Test Scenario: Mid-project adoption

1. Open an **existing project** that has never used IDE Memory
2. Ask: _"Learn about this project and save it to memory"_
3. Verify: agent uses `bootstrap_memory` prompt flow — analyzes README, package files, and populates all 4 sections

### Test Scenario: Stale memory detection

1. Set up a project and write memory
2. Wait a few days (or manually backdate timestamps in `meta.json`)
3. Reconnect → verify ⏰ stale warnings appear in summary
4. Ask agent to update → verify it refreshes the stale sections

### Checklist

| Check | Pass criteria |
|-------|---------------|
| Cross-IDE persistence | Content from IDE A readable in IDE B |
| Project reconnection | Same project recognized by path or git remote |
| Summary mode default | `read_memory` returns table, not content |
| Selective loading | Agent only loads sections it needs |
| Smart warnings | Stale/empty/large sections flagged |
| Append mode | Previous content preserved |
| MCP prompts available | All 3 prompts visible in IDE's prompt list |
| Bootstrap flow | Agent can populate memory from scratch |
| Update flow | Agent updates memory after changes |

---

## 4. Edge Cases

- **Large memory**: Write 10k+ chars to a section → `maxChars=200` truncation should work, summary shows 📦 flag
- **Empty project**: `read_memory` on fresh project → summary shows all sections as empty
- **Invalid section names**: Write to uppercase/hyphen/space names → clear error
- **Nonexistent project**: `read_memory("fake_id")` → "not found"
- **Git remote matching**: Init by path in IDE A, init by different path but same git remote in IDE B → should reconnect
- **Custom sections**: Write to `api_contracts` → appears in section list, loads selectively

---

## 5. Performance

- `init_project`: <500ms (git remote read from .git/config, no subprocess)
- `read_memory` summary: <100ms (only reads file sizes, not content)
- `read_memory` selective: <200ms (reads only requested files)
- No files created in user's project directory — all under `~/.ide-memory/`
