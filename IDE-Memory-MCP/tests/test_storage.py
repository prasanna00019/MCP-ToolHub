"""Tests for the storage module."""

import os
import tempfile
from pathlib import Path

import pytest

from ide_memory_mcp.storage import MemoryStorage, _normalize_path, _normalize_git_url, is_valid_section_name
from ide_memory_mcp.models import ProjectMeta, MEMORY_SECTIONS


# ---------------------------------------------------------------------------
# Unit tests — path / URL normalization
# ---------------------------------------------------------------------------

def test_normalize_path():
    """Test path normalization works correctly."""
    if os.name == "nt":
        assert _normalize_path("C:\\Users\\Test\\Project") == "c:/users/test/project"
        assert _normalize_path("C:/Users/Test/Project/") == "c:/users/test/project"
    else:
        assert _normalize_path("/home/user/project") == "/home/user/project"
        assert _normalize_path("/home/user/project/") == "/home/user/project"


def test_normalize_git_url():
    """Test git URL normalization."""
    assert _normalize_git_url("https://github.com/user/repo.git") == "github.com/user/repo"
    assert _normalize_git_url("https://github.com/user/repo") == "github.com/user/repo"
    assert _normalize_git_url("git@github.com:user/repo.git") == "github.com/user/repo"
    assert _normalize_git_url("git@github.com:user/repo") == "github.com/user/repo"
    assert _normalize_git_url("HTTPS://GITHUB.COM/USER/REPO") == "github.com/user/repo"


def test_is_valid_section_name():
    """Test section name validation."""
    assert is_valid_section_name("overview")
    assert is_valid_section_name("api_documentation")
    assert is_valid_section_name("test123")

    assert not is_valid_section_name("Overview")  # uppercase
    assert not is_valid_section_name("123test")   # starts with digit
    assert not is_valid_section_name("")          # empty
    assert not is_valid_section_name("test-test") # hyphen


# ---------------------------------------------------------------------------
# MemoryStorage integration tests
# ---------------------------------------------------------------------------

class TestMemoryStorage:
    """Test the MemoryStorage class."""

    @pytest.fixture
    def temp_storage(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = MemoryStorage(Path(tmpdir))
            yield storage

    def test_init_project_creates_files(self, temp_storage):
        """init_project should create meta.json and default section files."""
        project_path = "/test/project"
        meta, is_new = temp_storage.init_project(project_path, "Test Project")

        assert is_new
        assert meta.project_name == "Test Project"
        assert meta.project_path == project_path

        project_dir = temp_storage._project_dir(meta.project_id)
        assert project_dir.exists()
        assert temp_storage._meta_path(meta.project_id).exists()

        for section in MEMORY_SECTIONS:
            section_path = temp_storage._section_path(meta.project_id, section)
            assert section_path.exists()

    def test_reconnect_existing_project(self, temp_storage):
        """Calling init_project twice with the same path should not create a duplicate."""
        meta1, is_new1 = temp_storage.init_project("/test/project", "My Project")
        assert is_new1

        meta2, is_new2 = temp_storage.init_project("/test/project", "My Project")
        assert not is_new2
        assert meta1.project_id == meta2.project_id

    def test_update_and_get_section(self, temp_storage):
        """Overwriting a section should be retrievable."""
        meta, _ = temp_storage.init_project("/test/project", "Test Project")

        content = "# Test Content\n\nThis is a test."
        temp_storage.update_section(meta.project_id, "overview", content)

        retrieved = temp_storage.get_section(meta.project_id, "overview")
        assert retrieved == content

    def test_get_section_size(self, temp_storage):
        """get_section_size should return byte count without loading content."""
        meta, _ = temp_storage.init_project("/test/project", "Test")

        content = "Hello, world!"
        temp_storage.update_section(meta.project_id, "overview", content)

        size = temp_storage.get_section_size(meta.project_id, "overview")
        assert size > 0

    def test_append_to_section(self, temp_storage):
        """Appending should preserve existing content."""
        meta, _ = temp_storage.init_project("/test/project", "Test")

        temp_storage.update_section(meta.project_id, "decisions", "# Decisions\n\nFirst entry.")
        temp_storage.append_to_section(meta.project_id, "decisions", "Second entry.", heading="Auth Strategy")

        content = temp_storage.get_section(meta.project_id, "decisions")
        assert "First entry." in content
        assert "Second entry." in content
        assert "Auth Strategy" in content

    def test_load_sections_filter(self, temp_storage):
        """load_sections should only return requested sections."""
        meta, _ = temp_storage.init_project("/test/project", "Test")

        temp_storage.update_section(meta.project_id, "overview", "Overview content here")
        temp_storage.update_section(meta.project_id, "decisions", "Decisions content here")
        temp_storage.update_section(meta.project_id, "progress", "Progress content here")

        result = temp_storage.load_sections(meta.project_id, ["overview", "decisions"])
        assert "overview" in result
        assert "decisions" in result
        assert "progress" not in result

    def test_search_memory(self, temp_storage):
        """Search should find keywords across sections."""
        meta, _ = temp_storage.init_project("/test/project", "Test Project")

        content = "# Overview\n\nThis document contains important information about the project."
        temp_storage.update_section(meta.project_id, "overview", content)

        results = temp_storage.search_memory(meta.project_id, "important")
        assert "overview" in results
        assert len(results["overview"]) > 0

    def test_search_no_results(self, temp_storage):
        """Search for nonexistent term should return empty dict."""
        meta, _ = temp_storage.init_project("/test/project", "Test")
        results = temp_storage.search_memory(meta.project_id, "xyznonexistent")
        assert results == {}

    def test_section_history(self, temp_storage):
        """Overwriting a section should save the previous version to history."""
        meta, _ = temp_storage.init_project("/test/project", "Test")

        temp_storage.update_section(meta.project_id, "overview", "Version 1")
        temp_storage.update_section(meta.project_id, "overview", "Version 2")

        history = temp_storage.get_section_history(meta.project_id, "overview")
        assert len(history) >= 1  # At least one snapshot saved

    def test_custom_section(self, temp_storage):
        """Writing to a custom section name should work."""
        meta, _ = temp_storage.init_project("/test/project", "Test")

        temp_storage.update_section(meta.project_id, "api_contracts", "My API contracts")
        content = temp_storage.get_section(meta.project_id, "api_contracts")
        assert "API contracts" in content

        # Should appear in section names
        all_names = temp_storage.get_all_section_names(meta.project_id)
        assert "api_contracts" in all_names

    def test_delete_project(self, temp_storage):
        """Deleting a project should remove its directory."""
        meta, _ = temp_storage.init_project("/test/project", "Test")
        project_dir = temp_storage._project_dir(meta.project_id)
        assert project_dir.exists()

        assert temp_storage.delete_project(meta.project_id) is True
        assert not project_dir.exists()

    def test_list_projects(self, temp_storage):
        """list_projects should return all registered projects."""
        temp_storage.init_project("/test/project1", "Project 1")
        temp_storage.init_project("/test/project2", "Project 2")

        projects = temp_storage.list_projects()
        names = {p.project_name for p in projects}
        assert "Project 1" in names
        assert "Project 2" in names