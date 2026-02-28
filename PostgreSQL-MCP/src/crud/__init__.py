"""
CRUD operations module for PostgreSQL MCP.
Provides safe, parameterized database operations for Create, Read, Update, Delete.
"""

from .crud_manager import (
    create_record,
    create_records_batch,
    create_table,
    create_view,
    create_index,
    query_data,
    # query_with_joins,
    get_records,
    get_record_count,
    distinct_values,
    paginate_data,
    update_record,
    update_records_batch,
    update_column,
    rename_table,
    rename_column,
    delete_record,
    delete_records,
    truncate_table,
    drop_table,
)

__all__ = [
    "create_record",
    "create_records_batch",
    "create_table",
    "create_view",
    "create_index",
    "query_data",
    "query_with_joins",
    "get_records",
    "get_record_count",
    "distinct_values",
    "paginate_data",
    "update_record",
    "update_records_batch",
    "update_column",
    "rename_table",
    "rename_column",
    "delete_record",
    "delete_records",
    "truncate_table",
    "drop_table",
]
