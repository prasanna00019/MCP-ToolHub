"""
CRUD Manager: Handle Create, Read, Update, Delete operations for PostgreSQL.
All operations are parameterized for SQL injection prevention.
"""

import time
from typing import Any, Dict, List, Optional, Tuple
from src.database import get_connection
from .crud_validator import CRUDValidator


def _format_result(
    status: str,
    operation: str,
    rows_affected: int = 0,
    duration_ms: float = 0,
    result: Any = None,
    message: str = "",
    warnings: List[str] = None,
) -> Dict:
    """
    Format operation result in standard format.
    
    Args:
        status: one of 'success', 'error', 'warning'
        operation: name of the operation performed
        rows_affected: number of rows affected
        duration_ms: execution time in milliseconds
        result: operation-specific result data
        message: human-readable message
        warnings: list of warning messages
        
    Returns:
        Standardized result dictionary
    """
    return {
        "status": status,
        "operation": operation,
        "rows_affected": rows_affected,
        "duration_ms": round(duration_ms, 2),
        "result": result,
        "message": message,
        "warnings": warnings or [],
    }


# ============================================
# CREATE OPERATIONS
# ============================================

def create_record(table_name: str, values: Dict[str, Any]) -> Dict:
    """
    Insert a single record into a table (parameterized).
    
    Args:
        table_name: Name of the table
        values: Dictionary of column_name: value pairs
        
    Returns:
        Result with inserted record count
    """
    start = time.time()
    
    try:
        CRUDValidator.validate_table_name(table_name)
        CRUDValidator.validate_values_dict(values)
        
        conn = get_connection()
        cur = conn.cursor()
        
        # Build INSERT query with placeholders
        columns = list(values.keys())
        placeholders = ','.join(['%s'] * len(columns))
        col_names = ','.join(columns)
        
        query = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})"
        values_list = [values[col] for col in columns]
        
        cur.execute(query, values_list)
        conn.commit()
        
        duration = (time.time() - start) * 1000
        
        cur.close()
        conn.close()
        
        return _format_result(
            status="success",
            operation="create_record",
            rows_affected=1,
            duration_ms=duration,
            message=f"Record inserted successfully into '{table_name}'"
        )
    
    except Exception as e:
        return _format_result(
            status="error",
            operation="create_record",
            duration_ms=(time.time() - start) * 1000,
            message=str(e)
        )


def create_records_batch(table_name: str, records: List[Dict[str, Any]]) -> Dict:
    """
    Insert multiple records in a batch (more efficient than single inserts).
    
    Args:
        table_name: Name of the table
        records: List of dictionaries with column_name: value pairs
        
    Returns:
        Result with number of inserted records
    """
    start = time.time()
    
    try:
        CRUDValidator.validate_table_name(table_name)
        CRUDValidator.validate_values_list(records)
        
        conn = get_connection()
        cur = conn.cursor()
        
        # Get column structure from first record
        columns = list(records[0].keys())
        placeholders = ','.join(['%s'] * len(columns))
        col_names = ','.join(columns)
        
        query = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})"
        
        # Prepare all value tuples
        values_tuples = [
            tuple(record[col] for col in columns)
            for record in records
        ]
        
        # Execute batch insert
        cur.executemany(query, values_tuples)
        conn.commit()
        
        duration = (time.time() - start) * 1000
        rows_affected = len(records)
        
        cur.close()
        conn.close()
        
        return _format_result(
            status="success",
            operation="create_records_batch",
            rows_affected=rows_affected,
            duration_ms=duration,
            message=f"Batch inserted {rows_affected} records into '{table_name}'"
        )
    
    except Exception as e:
        return _format_result(
            status="error",
            operation="create_records_batch",
            duration_ms=(time.time() - start) * 1000,
            message=str(e)
        )


def create_table(
    table_name: str,
    columns: List[Dict[str, Any]],
    primary_key: Optional[List[str]] = None,
) -> Dict:
    """
    Create a new table with specified columns and constraints.
    
    Args:
        table_name: Name of the new table
        columns: List of column definitions:
            [
                {"name": "id", "type": "INTEGER", "nullable": False},
                {"name": "name", "type": "VARCHAR(255)", "nullable": False},
                {"name": "email", "type": "VARCHAR(255)", "nullable": True},
            ]
        primary_key: List of column names for primary key ['id'] or ['org_id', 'project_id']
        
    Returns:
        Result of table creation
    """
    start = time.time()
    
    try:
        CRUDValidator.validate_table_name(table_name)
        
        # Validate columns
        if not columns or not isinstance(columns, list):
            raise ValueError("Columns must be a non-empty list")
        
        col_definitions = []
        for col in columns:
            name = col.get("name")
            dtype = col.get("type")
            nullable = col.get("nullable", True)
            
            CRUDValidator.validate_column_name(name)
            CRUDValidator.validate_column_type(dtype)
            
            null_str = "" if nullable else " NOT NULL"
            col_definitions.append(f"{name} {dtype}{null_str}")
        
        # Add primary key constraint if specified
        if primary_key:
            CRUDValidator.validate_primary_key(primary_key)
            pk_cols = ','.join(primary_key)
            col_definitions.append(f"PRIMARY KEY ({pk_cols})")
        
        col_def_str = ',\n  '.join(col_definitions)
        query = f"CREATE TABLE {table_name} (\n  {col_def_str}\n)"
        
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(query)
        conn.commit()
        
        duration = (time.time() - start) * 1000
        
        cur.close()
        conn.close()
        
        return _format_result(
            status="success",
            operation="create_table",
            duration_ms=duration,
            message=f"Table '{table_name}' created successfully",
            result={"columns": len(columns), "has_primary_key": bool(primary_key)}
        )
    
    except Exception as e:
        return _format_result(
            status="error",
            operation="create_table",
            duration_ms=(time.time() - start) * 1000,
            message=str(e)
        )


def create_view(
    view_name: str,
    select_query: str,
    replace_if_exists: bool = False,
) -> Dict:
    """
    Create a database view from a SELECT query.
    
    Args:
        view_name: Name of the new view
        select_query: SELECT query to use for the view
        replace_if_exists: Use CREATE OR REPLACE (must have same columns)
        
    Returns:
        Result of view creation
    """
    start = time.time()
    
    try:
        CRUDValidator.validate_table_name(view_name)
        
        if not select_query or not isinstance(select_query, str):
            raise ValueError("select_query must be a non-empty string")
        
        create_or_replace = "CREATE OR REPLACE" if replace_if_exists else "CREATE"
        query = f"{create_or_replace} VIEW {view_name} AS {select_query}"
        
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(query)
        conn.commit()
        
        duration = (time.time() - start) * 1000
        
        cur.close()
        conn.close()
        
        return _format_result(
            status="success",
            operation="create_view",
            duration_ms=duration,
            message=f"View '{view_name}' created successfully"
        )
    
    except Exception as e:
        return _format_result(
            status="error",
            operation="create_view",
            duration_ms=(time.time() - start) * 1000,
            message=str(e)
        )


def create_index(
    index_name: str,
    table_name: str,
    columns: List[str],
    unique: bool = False,
) -> Dict:
    """
    Create a single or composite index on table columns.
    
    Args:
        index_name: Name of the index
        table_name: Table to create index on
        columns: List of column names ["name"] or ["first_name", "last_name"]
        unique: Whether to create a UNIQUE index
        
    Returns:
        Result of index creation
    """
    start = time.time()
    
    try:
        CRUDValidator.validate_table_name(index_name)
        CRUDValidator.validate_table_name(table_name)
        
        if not columns or not isinstance(columns, list):
            raise ValueError("Columns must be a non-empty list")
        
        for col in columns:
            CRUDValidator.validate_column_name(col)
        
        unique_str = "UNIQUE " if unique else ""
        col_str = ','.join(columns)
        query = f"CREATE {unique_str}INDEX {index_name} ON {table_name} ({col_str})"
        
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(query)
        conn.commit()
        
        duration = (time.time() - start) * 1000
        
        cur.close()
        conn.close()
        
        return _format_result(
            status="success",
            operation="create_index",
            duration_ms=duration,
            message=f"Index '{index_name}' created on '{table_name}({col_str})'",
            result={"unique": unique, "column_count": len(columns)}
        )
    
    except Exception as e:
        return _format_result(
            status="error",
            operation="create_index",
            duration_ms=(time.time() - start) * 1000,
            message=str(e)
        )


# ============================================
# READ OPERATIONS
# ============================================

def query_data(
    query: str,
    params: Optional[List[Any]] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> Dict:
    """
    Execute a SELECT query with optional pagination.
    
    Args:
        query: SELECT SQL query (can use %s for parameterized values)
        params: List of parameter values to substitute in query
        limit: Maximum number of rows to return
        offset: Number of rows to skip
        
    Returns:
        Result with rows and metadata
    """
    start = time.time()
    
    try:
        if not query or not isinstance(query, str):
            raise ValueError("Query must be a non-empty string")
        
        CRUDValidator.validate_limit_offset(limit, offset)
        
        # Add LIMIT/OFFSET to query if specified
        if limit is not None or offset is not None:
            limit_str = f"LIMIT {limit}" if limit is not None else ""
            offset_str = f"OFFSET {offset}" if offset is not None else ""
            query = f"{query} {limit_str} {offset_str}".strip()
        
        conn = get_connection()
        cur = conn.cursor()
        
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)
        
        rows = cur.fetchall()
        col_names = [desc[0] for desc in cur.description] if cur.description else []
        
        # Convert rows to list of dicts
        results = [dict(zip(col_names, row)) for row in rows]
        
        duration = (time.time() - start) * 1000
        
        cur.close()
        conn.close()
        
        return _format_result(
            status="success",
            operation="query_data",
            rows_affected=len(results),
            duration_ms=duration,
            result={"rows": results, "columns": col_names},
            message=f"Query returned {len(results)} rows"
        )
    
    except Exception as e:
        return _format_result(
            status="error",
            operation="query_data",
            duration_ms=(time.time() - start) * 1000,
            message=str(e)
        )


def get_records(
    table_name: str,
    where_clause: Optional[str] = None,
    where_params: Optional[List[Any]] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    order_by: Optional[str] = None,
) -> Dict:
    """
    Get records from a table with filtering and sorting.
    
    Args:
        table_name: Name of the table
        where_clause: WHERE condition (use %s for parameters, e.g., "age > %s AND city = %s")
        where_params: List of values for WHERE clause [30, "NYC"]
        limit: Maximum records to return
        offset: Number of records to skip
        order_by: ORDER BY clause (e.g., "name ASC, age DESC")
        
    Returns:
        Result with matching records
    """
    start = time.time()
    
    try:
        CRUDValidator.validate_table_name(table_name)
        CRUDValidator.validate_where_clause(where_clause)
        CRUDValidator.validate_limit_offset(limit, offset)
        CRUDValidator.validate_order_by(order_by)
        
        query = f"SELECT * FROM {table_name}"
        params = where_params or []
        
        if where_clause:
            query += f" WHERE {where_clause}"
        
        if order_by:
            query += f" ORDER BY {order_by}"
        
        if limit is not None:
            query += f" LIMIT {limit}"
        
        if offset is not None:
            query += f" OFFSET {offset}"
        
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute(query, params)
        rows = cur.fetchall()
        col_names = [desc[0] for desc in cur.description]
        
        results = [dict(zip(col_names, row)) for row in rows]
        
        duration = (time.time() - start) * 1000
        
        cur.close()
        conn.close()
        
        return _format_result(
            status="success",
            operation="get_records",
            rows_affected=len(results),
            duration_ms=duration,
            result={"records": results, "columns": col_names},
            message=f"Retrieved {len(results)} records from '{table_name}'"
        )
    
    except Exception as e:
        return _format_result(
            status="error",
            operation="get_records",
            duration_ms=(time.time() - start) * 1000,
            message=str(e)
        )


def get_record_count(
    table_name: str,
    where_clause: Optional[str] = None,
    where_params: Optional[List[Any]] = None,
) -> Dict:
    """
    Count records in a table with optional filtering.
    
    Args:
        table_name: Name of the table
        where_clause: Optional WHERE condition (e.g., "status = %s")
        where_params: List of values for WHERE clause
        
    Returns:
        Result with record count
    """
    start = time.time()
    
    try:
        CRUDValidator.validate_table_name(table_name)
        CRUDValidator.validate_where_clause(where_clause)
        
        query = f"SELECT COUNT(*) FROM {table_name}"
        params = where_params or []
        
        if where_clause:
            query += f" WHERE {where_clause}"
        
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute(query, params)
        count = cur.fetchone()[0]
        
        duration = (time.time() - start) * 1000
        
        cur.close()
        conn.close()
        
        return _format_result(
            status="success",
            operation="get_record_count",
            duration_ms=duration,
            result={"count": count},
            message=f"Table '{table_name}' has {count} records"
        )
    
    except Exception as e:
        return _format_result(
            status="error",
            operation="get_record_count",
            duration_ms=(time.time() - start) * 1000,
            message=str(e)
        )


def distinct_values(
    table_name: str,
    column_name: str,
    limit: Optional[int] = None,
) -> Dict:
    """
    Get distinct values for a column.
    
    Args:
        table_name: Name of the table
        column_name: Column to get distinct values from
        limit: Maximum values to return
        
    Returns:
        Result with distinct values
    """
    start = time.time()
    
    try:
        CRUDValidator.validate_table_name(table_name)
        CRUDValidator.validate_column_name(column_name)
        CRUDValidator.validate_limit_offset(limit, None)
        
        query = f"SELECT DISTINCT {column_name} FROM {table_name} ORDER BY {column_name}"
        
        if limit:
            query += f" LIMIT {limit}"
        
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute(query)
        values = [row[0] for row in cur.fetchall()]
        
        duration = (time.time() - start) * 1000
        
        cur.close()
        conn.close()
        
        return _format_result(
            status="success",
            operation="distinct_values",
            rows_affected=len(values),
            duration_ms=duration,
            result={"values": values, "count": len(values)},
            message=f"Found {len(values)} distinct values in '{table_name}.{column_name}'"
        )
    
    except Exception as e:
        return _format_result(
            status="error",
            operation="distinct_values",
            duration_ms=(time.time() - start) * 1000,
            message=str(e)
        )


def paginate_data(
    table_name: str,
    page: int = 1,
    page_size: int = 10,
    order_by: Optional[str] = None,
    where_clause: Optional[str] = None,
    where_params: Optional[List[Any]] = None,
) -> Dict:
    """
    Get paginated records from a table.
    
    Args:
        table_name: Name of the table
        page: Page number (1-indexed)
        page_size: Records per page
        order_by: ORDER BY clause for consistent pagination
        where_clause: Optional WHERE condition
        where_params: Parameters for WHERE clause
        
    Returns:
        Result with paginated records and metadata
    """
    start = time.time()
    
    try:
        CRUDValidator.validate_table_name(table_name)
        
        if not isinstance(page, int) or page < 1:
            raise ValueError("Page must be a positive integer")
        if not isinstance(page_size, int) or page_size < 1:
            raise ValueError("Page size must be a positive integer")
        
        CRUDValidator.validate_where_clause(where_clause)
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM {table_name}"
        params = where_params or []
        if where_clause:
            count_query += f" WHERE {where_clause}"
        
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute(count_query, params)
        total_count = cur.fetchone()[0]
        
        # Get paginated data
        query = f"SELECT * FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"
        if order_by:
            query += f" ORDER BY {order_by}"
        query += f" LIMIT {page_size} OFFSET {offset}"
        
        cur.execute(query, params)
        rows = cur.fetchall()
        col_names = [desc[0] for desc in cur.description]
        
        records = [dict(zip(col_names, row)) for row in rows]
        
        total_pages = (total_count + page_size - 1) // page_size
        
        duration = (time.time() - start) * 1000
        
        cur.close()
        conn.close()
        
        return _format_result(
            status="success",
            operation="paginate_data",
            rows_affected=len(records),
            duration_ms=duration,
            result={
                "records": records,
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_records": total_count,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_previous": page > 1,
                }
            },
            message=f"Page {page} of {total_pages} ({len(records)} records)"
        )
    
    except Exception as e:
        return _format_result(
            status="error",
            operation="paginate_data",
            duration_ms=(time.time() - start) * 1000,
            message=str(e)
        )


# ============================================
# UPDATE OPERATIONS
# ============================================

def update_record(
    table_name: str,
    record_id: Any,
    id_column: str,
    values: Dict[str, Any],
) -> Dict:
    """
    Update a single record by ID.
    
    Args:
        table_name: Name of the table
        record_id: Value of the ID column
        id_column: Name of the ID column (usually 'id')
        values: Dictionary of column_name: new_value pairs
        
    Returns:
        Result of update operation
    """
    start = time.time()
    
    try:
        CRUDValidator.validate_table_name(table_name)
        CRUDValidator.validate_column_name(id_column)
        CRUDValidator.validate_values_dict(values)
        
        # Build UPDATE query
        set_clause = ','.join([f"{col}=%s" for col in values.keys()])
        query = f"UPDATE {table_name} SET {set_clause} WHERE {id_column}=%s"
        
        # Prepare values list
        param_values = list(values.values()) + [record_id]
        
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute(query, param_values)
        conn.commit()
        
        rows_affected = cur.rowcount
        duration = (time.time() - start) * 1000
        
        cur.close()
        conn.close()
        
        if rows_affected == 0:
            return _format_result(
                status="warning",
                operation="update_record",
                duration_ms=duration,
                message=f"No records found with {id_column}={record_id}"
            )
        
        return _format_result(
            status="success",
            operation="update_record",
            rows_affected=rows_affected,
            duration_ms=duration,
            message=f"Updated {rows_affected} record(s) in '{table_name}'"
        )
    
    except Exception as e:
        return _format_result(
            status="error",
            operation="update_record",
            duration_ms=(time.time() - start) * 1000,
            message=str(e)
        )


def update_records_batch(
    table_name: str,
    where_clause: str,
    where_params: List[Any],
    values: Dict[str, Any],
) -> Dict:
    """
    Update multiple records matching a WHERE clause.
    
    Args:
        table_name: Name of the table
        where_clause: WHERE condition (e.g., "age > %s AND city = %s")
        where_params: Values for WHERE clause
        values: Dictionary of column_name: new_value pairs to update
        
    Returns:
        Result with number of updated records
    """
    start = time.time()
    
    try:
        CRUDValidator.validate_table_name(table_name)
        CRUDValidator.validate_where_clause(where_clause)
        CRUDValidator.validate_values_dict(values)
        
        # Build UPDATE query
        set_clause = ','.join([f"{col}=%s" for col in values.keys()])
        query = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"
        
        # Prepare parameters: update values + where params
        params = list(values.values()) + where_params
        
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute(query, params)
        conn.commit()
        
        rows_affected = cur.rowcount
        duration = (time.time() - start) * 1000
        
        cur.close()
        conn.close()
        
        status = "success" if rows_affected > 0 else "warning"
        msg = f"Updated {rows_affected} record(s)" if rows_affected > 0 else "No records matched WHERE clause"
        
        return _format_result(
            status=status,
            operation="update_records_batch",
            rows_affected=rows_affected,
            duration_ms=duration,
            message=msg
        )
    
    except Exception as e:
        return _format_result(
            status="error",
            operation="update_records_batch",
            duration_ms=(time.time() - start) * 1000,
            message=str(e)
        )


def update_column(
    table_name: str,
    column_name: str,
    new_value: Any,
    where_clause: Optional[str] = None,
    where_params: Optional[List[Any]] = None,
) -> Dict:
    """
    Bulk update a single column in multiple records.
    
    Args:
        table_name: Name of the table
        column_name: Column to update
        new_value: New value for the column
        where_clause: Optional WHERE condition (if None, updates ALL records!)
        where_params: Parameters for WHERE clause
        
    Returns:
        Result with number of updated records
    """
    start = time.time()
    
    try:
        CRUDValidator.validate_table_name(table_name)
        CRUDValidator.validate_column_name(column_name)
        CRUDValidator.validate_where_clause(where_clause)
        
        if not where_clause:
            # Warn about updating all records
            warnings_list = ["WARNING: No WHERE clause specified - will update ALL records in table!"]
        else:
            warnings_list = []
        
        query = f"UPDATE {table_name} SET {column_name}=%s"
        params = [new_value]
        
        if where_clause:
            query += f" WHERE {where_clause}"
            params.extend(where_params or [])
        
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute(query, params)
        conn.commit()
        
        rows_affected = cur.rowcount
        duration = (time.time() - start) * 1000
        
        cur.close()
        conn.close()
        
        return _format_result(
            status="success",
            operation="update_column",
            rows_affected=rows_affected,
            duration_ms=duration,
            message=f"Updated {rows_affected} record(s)",
            warnings=warnings_list
        )
    
    except Exception as e:
        return _format_result(
            status="error",
            operation="update_column",
            duration_ms=(time.time() - start) * 1000,
            message=str(e)
        )


def rename_table(old_name: str, new_name: str) -> Dict:
    """
    Rename a table safely.
    
    Args:
        old_name: Current table name
        new_name: New table name
        
    Returns:
        Result of rename operation
    """
    start = time.time()
    
    try:
        CRUDValidator.validate_table_name(old_name)
        CRUDValidator.validate_table_name(new_name)
        
        query = f"ALTER TABLE {old_name} RENAME TO {new_name}"
        
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute(query)
        conn.commit()
        
        duration = (time.time() - start) * 1000
        
        cur.close()
        conn.close()
        
        return _format_result(
            status="success",
            operation="rename_table",
            duration_ms=duration,
            message=f"Table '{old_name}' renamed to '{new_name}'"
        )
    
    except Exception as e:
        return _format_result(
            status="error",
            operation="rename_table",
            duration_ms=(time.time() - start) * 1000,
            message=str(e)
        )


def rename_column(
    table_name: str,
    old_column: str,
    new_column: str,
) -> Dict:
    """
    Rename a column in a table.
    
    Args:
        table_name: Name of the table
        old_column: Current column name
        new_column: New column name
        
    Returns:
        Result of rename operation
    """
    start = time.time()
    
    try:
        CRUDValidator.validate_table_name(table_name)
        CRUDValidator.validate_column_name(old_column)
        CRUDValidator.validate_column_name(new_column)
        
        query = f"ALTER TABLE {table_name} RENAME COLUMN {old_column} TO {new_column}"
        
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute(query)
        conn.commit()
        
        duration = (time.time() - start) * 1000
        
        cur.close()
        conn.close()
        
        return _format_result(
            status="success",
            operation="rename_column",
            duration_ms=duration,
            message=f"Column '{old_column}' renamed to '{new_column}' in '{table_name}'"
        )
    
    except Exception as e:
        return _format_result(
            status="error",
            operation="rename_column",
            duration_ms=(time.time() - start) * 1000,
            message=str(e)
        )


# ============================================
# DELETE OPERATIONS
# ============================================

def delete_record(
    table_name: str,
    record_id: Any,
    id_column: str,
) -> Dict:
    """
    Delete a single record by ID.
    
    Args:
        table_name: Name of the table
        record_id: Value of the ID column
        id_column: Name of the ID column (usually 'id')
        
    Returns:
        Result of delete operation
    """
    start = time.time()
    
    try:
        CRUDValidator.validate_table_name(table_name)
        CRUDValidator.validate_column_name(id_column)
        
        query = f"DELETE FROM {table_name} WHERE {id_column}=%s"
        
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute(query, [record_id])
        conn.commit()
        
        rows_affected = cur.rowcount
        duration = (time.time() - start) * 1000
        
        cur.close()
        conn.close()
        
        if rows_affected == 0:
            return _format_result(
                status="warning",
                operation="delete_record",
                duration_ms=duration,
                message=f"No records found with {id_column}={record_id}"
            )
        
        return _format_result(
            status="success",
            operation="delete_record",
            rows_affected=rows_affected,
            duration_ms=duration,
            message=f"Deleted {rows_affected} record(s) from '{table_name}'"
        )
    
    except Exception as e:
        return _format_result(
            status="error",
            operation="delete_record",
            duration_ms=(time.time() - start) * 1000,
            message=str(e)
        )


def delete_records(
    table_name: str,
    where_clause: str,
    where_params: List[Any],
) -> Dict:
    """
    Delete multiple records matching a WHERE clause.
    
    Args:
        table_name: Name of the table
        where_clause: WHERE condition (e.g., "status = %s AND age < %s")
        where_params: Values for WHERE clause
        
    Returns:
        Result with number of deleted records
    """
    start = time.time()
    
    try:
        CRUDValidator.validate_table_name(table_name)
        CRUDValidator.validate_where_clause(where_clause)
        
        query = f"DELETE FROM {table_name} WHERE {where_clause}"
        
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute(query, where_params)
        conn.commit()
        
        rows_affected = cur.rowcount
        duration = (time.time() - start) * 1000
        
        cur.close()
        conn.close()
        
        status = "success" if rows_affected > 0 else "warning"
        msg = f"Deleted {rows_affected} record(s)" if rows_affected > 0 else "No records matched WHERE clause"
        
        return _format_result(
            status=status,
            operation="delete_records",
            rows_affected=rows_affected,
            duration_ms=duration,
            message=msg
        )
    
    except Exception as e:
        return _format_result(
            status="error",
            operation="delete_records",
            duration_ms=(time.time() - start) * 1000,
            message=str(e)
        )


def truncate_table(table_name: str) -> Dict:
    """
    Truncate (clear all data from) a table. Much faster than DELETE for large tables.
    WARNING: This deletes all data! Cannot be rolled back in autocommit mode.
    
    Args:
        table_name: Name of the table to truncate
        
    Returns:
        Result of truncate operation
    """
    start = time.time()
    
    try:
        CRUDValidator.validate_table_name(table_name)
        
        query = f"TRUNCATE TABLE {table_name}"
        
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute(query)
        conn.commit()
        
        duration = (time.time() - start) * 1000
        
        cur.close()
        conn.close()
        
        warnings_list = [
            "WARNING: TRUNCATE deleted all data from table!",
            "This operation cannot be rolled back in some configurations."
        ]
        
        return _format_result(
            status="success",
            operation="truncate_table",
            duration_ms=duration,
            message=f"Truncated table '{table_name}' - all data deleted",
            warnings=warnings_list
        )
    
    except Exception as e:
        return _format_result(
            status="error",
            operation="truncate_table",
            duration_ms=(time.time() - start) * 1000,
            message=str(e)
        )


def drop_table(table_name: str, cascade: bool = False) -> Dict:
    """
    Drop (delete) a table from the database.
    WARNING: This is permanent and deletes the entire table structure and data!
    
    Args:
        table_name: Name of the table to drop
        cascade: If True, also drop dependent objects (views, indexes, etc.)
        
    Returns:
        Result of drop operation
    """
    start = time.time()
    
    try:
        CRUDValidator.validate_table_name(table_name)
        
        cascade_str = "CASCADE" if cascade else "RESTRICT"
        query = f"DROP TABLE {table_name} {cascade_str}"
        
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute(query)
        conn.commit()
        
        duration = (time.time() - start) * 1000
        
        cur.close()
        conn.close()
        
        warnings_list = [
            f"CRITICAL: Table '{table_name}' has been permanently dropped!",
            "This operation cannot be undone."
        ]
        
        return _format_result(
            status="success",
            operation="drop_table",
            duration_ms=duration,
            message=f"Table '{table_name}' dropped",
            warnings=warnings_list
        )
    
    except Exception as e:
        return _format_result(
            status="error",
            operation="drop_table",
            duration_ms=(time.time() - start) * 1000,
            message=str(e)
        )
