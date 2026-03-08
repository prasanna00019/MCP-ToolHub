"""Query Optimization Module - Phase 3A"""

from .query_optimizer import (
    explain_query,
    suggest_indexes,
    find_unused_indexes,
)

__all__ = [
    "explain_query",
    "suggest_indexes",
    "find_unused_indexes",
]
