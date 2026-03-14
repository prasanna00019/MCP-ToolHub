"""
Configuration system for IDE Memory MCP.

Minimal configuration — keeps things simple. Stored at ~/.ide-memory/config.json.
"""

import json
from pathlib import Path
from typing import Any


class Config:
    """Configuration manager for IDE Memory MCP."""

    def __init__(self, config_path: Path = None):
        if config_path is None:
            self.config_path = Path.home() / ".ide-memory" / "config.json"
        else:
            self.config_path = config_path

        self.defaults: dict[str, Any] = {
            "default_sections": [
                "overview",
                "decisions",
                "active_context",
                "progress",
            ],
        }

        self.config = self._load()

    def _load(self) -> dict[str, Any]:
        """Load configuration from file or return defaults."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    user_config = json.load(f)
                merged = self.defaults.copy()
                merged.update(user_config)
                return merged
            except (json.JSONDecodeError, IOError):
                return self.defaults.copy()

        # First run — write defaults
        self._save(self.defaults)
        return self.defaults.copy()

    def _save(self, config: dict[str, Any]) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.config[key] = value
        self._save(self.config)


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------
_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config


def reload_config() -> Config:
    global _config
    _config = Config()
    return _config