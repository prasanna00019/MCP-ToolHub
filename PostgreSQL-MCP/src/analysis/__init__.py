"""Analysis module for SchemaIntelligence"""

from .detector import detect_junction_tables, suggest_joins

__all__ = ["detect_junction_tables", "suggest_joins"]
