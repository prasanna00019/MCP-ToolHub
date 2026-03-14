"""Tests for the MCP server tool functions."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from ide_memory_mcp.storage import MemoryStorage
from ide_memory_mcp.models import MEMORY_SECTIONS


class TestServerTools:
    """Test the server tool functions end-to-end via the storage layer.

    These tests exercise the same codepaths the MCP tools use,
    without needing to spin up an actual MCP server.
    """

    @pytest.fixture
    def setup(self):
        """Create temp storage and patch the server's global storage instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = MemoryStorage(Path(tmpdir))
            with patch("ide_memory_mcp.server.storage", storage):
                # Import after patching
                from ide_memory_mcp.server import (
                    init_project, read_memory, write_memory, manage_projects
                )
                yield {
                    "storage": storage,
                    "init_project": init_project,
                    "read_memory": read_memory,
                    "write_memory": write_memory,
                    "manage_projects": manage_projects,
                }

    @pytest.mark.asyncio
    async def test_init_new_project(self, setup):
        """init_project should register a new project."""
        result = await setup["init_project"]("/test/myproject", "My Project")
        assert "New project registered" in result
        assert "My Project" in result

    @pytest.mark.asyncio
    async def test_init_reconnect(self, setup):
        """Calling init_project twice should reconnect, not create duplicate."""
        await setup["init_project"]("/test/myproject", "My Project")
        result = await setup["init_project"]("/test/myproject")
        assert "Memory Summary" in result

    @pytest.mark.asyncio
    async def test_read_memory_default_returns_summary(self, setup):
        """read_memory with no sections should return a summary table, NOT content."""
        await setup["init_project"]("/test/myproject", "Test")
        meta = setup["storage"].resolve_project("/test/myproject")

        setup["storage"].update_section(meta.project_id, "overview", "Big overview content " * 50)

        result = await setup["read_memory"](meta.project_id)
        assert "Memory Summary" in result
        assert "| Section" in result
        # Should NOT contain the actual content
        assert "Big overview content" not in result

    @pytest.mark.asyncio
    async def test_read_memory_selective(self, setup):
        """read_memory with sections filter should load only those sections."""
        await setup["init_project"]("/test/myproject", "Test")
        meta = setup["storage"].resolve_project("/test/myproject")

        setup["storage"].update_section(meta.project_id, "overview", "Overview here")
        setup["storage"].update_section(meta.project_id, "decisions", "Decisions here")

        result = await setup["read_memory"](meta.project_id, sections=["overview"])
        assert "Overview here" in result
        assert "Decisions here" not in result

    @pytest.mark.asyncio
    async def test_read_memory_max_chars(self, setup):
        """read_memory with maxChars should truncate long sections."""
        await setup["init_project"]("/test/myproject", "Test")
        meta = setup["storage"].resolve_project("/test/myproject")

        long_content = "A" * 5000
        setup["storage"].update_section(meta.project_id, "overview", long_content)

        result = await setup["read_memory"](meta.project_id, sections=["overview"], maxChars=100)
        assert "truncated" in result

    @pytest.mark.asyncio
    async def test_read_memory_search(self, setup):
        """read_memory with query should search across sections."""
        await setup["init_project"]("/test/myproject", "Test")
        meta = setup["storage"].resolve_project("/test/myproject")

        setup["storage"].update_section(meta.project_id, "overview", "We use PostgreSQL for the database.")

        result = await setup["read_memory"](meta.project_id, query="PostgreSQL")
        assert "PostgreSQL" in result
        assert "match" in result.lower()

    @pytest.mark.asyncio
    async def test_write_memory_overwrite(self, setup):
        """write_memory should overwrite section content."""
        await setup["init_project"]("/test/myproject", "Test")
        meta = setup["storage"].resolve_project("/test/myproject")

        result = await setup["write_memory"](
            meta.project_id,
            {"overview": "# Overview\n\nThis is a real project overview."}
        )
        assert "Updated 1 section(s)" in result

        content = setup["storage"].get_section(meta.project_id, "overview")
        assert "real project overview" in content

    @pytest.mark.asyncio
    async def test_write_memory_append(self, setup):
        """write_memory with append=True should preserve existing content."""
        await setup["init_project"]("/test/myproject", "Test")
        meta = setup["storage"].resolve_project("/test/myproject")

        await setup["write_memory"](
            meta.project_id,
            {"decisions": "Initial decision."}
        )
        await setup["write_memory"](
            meta.project_id,
            {"decisions": "New decision added."},
            append=True,
            heading="Auth Strategy"
        )

        content = setup["storage"].get_section(meta.project_id, "decisions")
        assert "Initial decision." in content
        assert "New decision added." in content
        assert "Auth Strategy" in content

    @pytest.mark.asyncio
    async def test_manage_projects_list(self, setup):
        """manage_projects list should return all projects."""
        await setup["init_project"]("/test/project1", "Project One")
        await setup["init_project"]("/test/project2", "Project Two")

        result = await setup["manage_projects"]("list")
        assert "Project One" in result
        assert "Project Two" in result

    @pytest.mark.asyncio
    async def test_manage_projects_delete(self, setup):
        """manage_projects delete should require confirmation."""
        result1 = await setup["init_project"]("/test/myproject", "Test")
        meta = setup["storage"].resolve_project("/test/myproject")

        # Without confirm
        result = await setup["manage_projects"]("delete", meta.project_id)
        assert "permanently delete" in result.lower() or "⚠️" in result

        # With confirm
        result = await setup["manage_projects"]("delete", meta.project_id, confirm=True)
        assert "Deleted" in result

    @pytest.mark.asyncio
    async def test_read_memory_not_found(self, setup):
        """read_memory for nonexistent project should return error."""
        result = await setup["read_memory"]("nonexistent_id")
        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_write_invalid_section_name(self, setup):
        """write_memory with invalid section name should fail gracefully."""
        await setup["init_project"]("/test/myproject", "Test")
        meta = setup["storage"].resolve_project("/test/myproject")

        result = await setup["write_memory"](
            meta.project_id,
            {"Invalid-Name": "content"}
        )
        assert "Invalid" in result

    @pytest.mark.asyncio
    async def test_init_new_project_mentions_bootstrap(self, setup):
        """New project init should mention bootstrap_memory prompt."""
        result = await setup["init_project"]("/test/newproject", "New Project")
        assert "bootstrap_memory" in result
        assert "write_memory" in result

    @pytest.mark.asyncio
    async def test_reconnect_shows_empty_warning(self, setup):
        """Reconnect to project with empty sections should warn about them."""
        await setup["init_project"]("/test/myproject", "Test")
        result = await setup["init_project"]("/test/myproject")
        # All default sections are essentially empty at this point
        assert "empty" in result.lower() or "⚠️" in result

    @pytest.mark.asyncio
    async def test_summary_shows_stale_warning(self, setup):
        """Summary should flag stale sections when they exist."""
        await setup["init_project"]("/test/myproject", "Test")
        meta = setup["storage"].resolve_project("/test/myproject")

        # Write content that's long enough (>50 chars) to not be classified as empty
        setup["storage"].update_section(
            meta.project_id, "overview",
            "Some overview content that describes the project architecture and tech stack in detail"
        )
        meta_obj = setup["storage"].get_project(meta.project_id)
        # Fake a stale timestamp (15 days ago)
        from datetime import datetime, timezone, timedelta
        old_ts = (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()
        meta_obj.sections_updated["overview"] = old_ts
        meta_obj.save(setup["storage"]._meta_path(meta.project_id))

        result = await setup["read_memory"](meta.project_id)
        assert "⏰" in result or "Stale" in result

    @pytest.mark.asyncio
    async def test_prune_mode_gives_instructions(self, setup):
        """Prune mode should include cleanup instructions."""
        await setup["init_project"]("/test/myproject", "Test")
        meta = setup["storage"].resolve_project("/test/myproject")

        setup["storage"].update_section(meta.project_id, "overview", "Some content to prune")
        result = await setup["read_memory"](meta.project_id, prune=True)
        assert "Remove" in result or "outdated" in result
        assert "write_memory" in result

    @pytest.mark.asyncio
    async def test_write_memory_shows_empty_reminder(self, setup):
        """After writing one section, write_memory should remind about still-empty sections."""
        await setup["init_project"]("/test/myproject", "Test")
        meta = setup["storage"].resolve_project("/test/myproject")

        result = await setup["write_memory"](
            meta.project_id,
            {"overview": "# My Project\n\nA great project."}
        )
        assert "Still empty" in result


class TestMCPPrompts:
    """Test that MCP prompts return proper content."""

    def test_start_session_prompt(self):
        """start_session prompt should include init_project instruction."""
        from ide_memory_mcp.server import start_session
        result = start_session("/test/project")
        assert "init_project" in result
        assert "read_memory" in result
        assert "write_memory" in result
        assert "/test/project" in result

    def test_bootstrap_memory_prompt(self):
        """bootstrap_memory prompt should guide through all sections."""
        from ide_memory_mcp.server import bootstrap_memory
        result = bootstrap_memory("/test/project")
        assert "overview" in result
        assert "decisions" in result
        assert "active_context" in result
        assert "progress" in result
        assert "write_memory" in result

    def test_update_memory_prompt(self):
        """update_memory prompt should mention reading current state and updating."""
        from ide_memory_mcp.server import update_memory
        result = update_memory("test-project-id")
        assert "read_memory" in result
        assert "write_memory" in result
        assert "active_context" in result
        assert "decisions" in result