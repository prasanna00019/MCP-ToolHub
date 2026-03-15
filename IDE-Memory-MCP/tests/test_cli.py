"""Tests for the CLI commands."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from ide_memory_mcp.cli import _merge_mcp_config, cmd_doctor, cmd_status


class TestMergeConfig:
    """Test the MCP config merge logic."""

    def test_creates_new_config(self):
        """Should create config file if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            assert not config_path.exists()

            result = _merge_mcp_config(config_path)
            assert result is True
            assert config_path.exists()

            config = json.loads(config_path.read_text())
            assert "mcpServers" in config
            assert "ide-memory" in config["mcpServers"]
            assert config["mcpServers"]["ide-memory"]["command"] == "ide-memory-mcp"

    def test_merges_with_existing_config(self):
        """Should merge with existing MCP servers, not overwrite them."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            existing = {
                "mcpServers": {
                    "other-server": {"command": "other-mcp"}
                }
            }
            config_path.write_text(json.dumps(existing))

            _merge_mcp_config(config_path)

            config = json.loads(config_path.read_text())
            assert "other-server" in config["mcpServers"]
            assert "ide-memory" in config["mcpServers"]

    def test_skips_if_already_configured(self):
        """Should return False if ide-memory is already configured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            existing = {
                "mcpServers": {
                    "ide-memory": {"command": "ide-memory-mcp"}
                }
            }
            config_path.write_text(json.dumps(existing))

            result = _merge_mcp_config(config_path)
            assert result is False

    def test_creates_parent_dirs(self):
        """Should create parent directories if they don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "deep" / "nested" / "mcp.json"
            result = _merge_mcp_config(config_path)
            assert result is True
            assert config_path.exists()

    def test_handles_malformed_json(self):
        """Should handle existing file with bad JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config_path.write_text("not json {{")

            result = _merge_mcp_config(config_path)
            assert result is True

            config = json.loads(config_path.read_text())
            assert "ide-memory" in config["mcpServers"]

    def test_supports_custom_root_key(self):
        """Should support custom root key like 'servers' for VS Code."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            result = _merge_mcp_config(config_path, root_key="servers")
            assert result is True
            
            config = json.loads(config_path.read_text())
            assert "servers" in config
            assert "mcpServers" not in config
            assert "ide-memory" in config["servers"]


class TestDoctorCommand:
    """Test the doctor command output."""

    def test_doctor_runs(self, capsys):
        """Doctor command should run without errors."""
        import argparse
        args = argparse.Namespace()
        cmd_doctor(args)

        output = capsys.readouterr().out
        assert "Health Check" in output
        assert "Server module" in output
        assert "Storage" in output


class TestStatusCommand:
    """Test the status command output."""

    def test_status_no_projects(self, capsys):
        """Status with no projects should show empty message."""
        import argparse
        with tempfile.TemporaryDirectory() as tmpdir:
            from ide_memory_mcp.storage import MemoryStorage
            storage = MemoryStorage(Path(tmpdir))
            with patch("ide_memory_mcp.cli.MemoryStorage", return_value=storage):
                args = argparse.Namespace()
                cmd_status(args)

                output = capsys.readouterr().out
                assert "No projects" in output

    def test_status_with_projects(self, capsys):
        """Status with projects should show project listing."""
        import argparse
        with tempfile.TemporaryDirectory() as tmpdir:
            from ide_memory_mcp.storage import MemoryStorage
            storage = MemoryStorage(Path(tmpdir))
            storage.init_project("/test/project", "Test Project")

            with patch("ide_memory_mcp.cli.MemoryStorage", return_value=storage):
                args = argparse.Namespace()
                cmd_status(args)

                output = capsys.readouterr().out
                assert "1 registered" in output
                assert "Test Project" in output
