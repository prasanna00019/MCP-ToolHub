"""
Schema Modification module.
Exports functions for advanced DDL operations (Phase 2).
"""

from .mod_manager import (
    schema_add_column,
    schema_modify_column_type,
    schema_drop_column,
    schema_set_column_nullable,
    schema_list_indexes,
    schema_drop_index,
    schema_list_constraints,
    schema_add_primary_key,
    schema_add_foreign_key,
    schema_drop_constraint,
    schema_list_views,
    schema_get_view_definition,
    schema_drop_view
)

__all__ = [
    "schema_add_column",
    "schema_modify_column_type",
    "schema_drop_column",
    "schema_set_column_nullable",
    "schema_list_indexes",
    "schema_drop_index",
    "schema_list_constraints",
    "schema_add_primary_key",
    "schema_add_foreign_key",
    "schema_drop_constraint",
    "schema_list_views",
    "schema_get_view_definition",
    "schema_drop_view"
]
