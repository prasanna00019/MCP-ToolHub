"""
Transaction Manager: Multi-operation transactions and table backups.
Phase 5A: execute_transaction, backup_table
"""

import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from src.database import get_connection


def _format_result(
    status: str,
    operation: str,
    rows_affected: int = 0,
    duration_ms: float = 0,
    result: Any = None,
    message: str = "",
    warnings: List[str] = None,
) -> Dict:
    """Format operation result in standard format."""
    return {
        "status": status,
        "operation": operation,
        "rows_affected": rows_affected,
        "duration_ms": round(duration_ms, 2),
        "result": result,
        "message": message,
        "warnings": warnings or [],
    }


def execute_transaction(
    operations: List[Dict[str, Any]],
    isolation_level: str = "READ COMMITTED"
) -> Dict:
    """
    Execute multiple operations in a single ACID transaction.
    
    Args:
        operations: List of operations to execute. Each operation is a dict with:
            - type: "query", "insert", "update", "delete"
            - For query: sql (string)
            - For insert: table (string), data (dict)
            - For update: table (string), where (string), values (dict)
            - For delete: table (string), where (string)
        isolation_level: Transaction isolation level
            - "READ UNCOMMITTED"
            - "READ COMMITTED" (default)
            - "REPEATABLE READ"
            - "SERIALIZABLE"
        
    Returns:
        Dictionary with transaction results
        
    Examples:
        execute_transaction([
            {"type": "insert", "table": "users", "data": {"name": "John", "email": "john@example.com"}},
            {"type": "update", "table": "orders", "where": "user_id = 1", "values": {"status": "active"}},
            {"type": "query", "sql": "SELECT COUNT(*) FROM users"}
        ])
    """
    start_time = time.time()
    warnings = []
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Validate isolation level
        valid_levels = ["READ UNCOMMITTED", "READ COMMITTED", "REPEATABLE READ", "SERIALIZABLE"]
        if isolation_level.upper() not in valid_levels:
            return _format_result(
                status="error",
                operation="execute_transaction",
                message=f"Invalid isolation_level '{isolation_level}'. Must be one of: {', '.join(valid_levels)}"
            )
        
        if not operations:
            return _format_result(
                status="error",
                operation="execute_transaction",
                message="No operations provided"
            )
        
        # Start transaction with specified isolation level
        cursor.execute(f"BEGIN ISOLATION LEVEL {isolation_level.upper()}")
        
        results = []
        total_rows_affected = 0
        
        try:
            for idx, op in enumerate(operations):
                op_type = op.get("type", "").lower()
                op_result = {}
                
                if op_type == "query":
                    # Execute raw SQL query
                    sql = op.get("sql")
                    if not sql:
                        raise ValueError(f"Operation {idx + 1}: 'sql' is required for query type")
                    
                    cursor.execute(sql)
                    
                    # Check if query returns results
                    if cursor.description:
                        rows = cursor.fetchall()
                        columns = [desc[0] for desc in cursor.description]
                        op_result = {
                            "type": "query",
                            "rows": [dict(zip(columns, row)) for row in rows],
                            "row_count": len(rows)
                        }
                        total_rows_affected += len(rows)
                    else:
                        op_result = {
                            "type": "query",
                            "rows_affected": cursor.rowcount
                        }
                        total_rows_affected += cursor.rowcount
                
                elif op_type == "insert":
                    # Insert operation
                    table = op.get("table")
                    data = op.get("data")
                    
                    if not table or not data:
                        raise ValueError(f"Operation {idx + 1}: 'table' and 'data' are required for insert type")
                    
                    columns = list(data.keys())
                    values = list(data.values())
                    placeholders = ", ".join(["%s"] * len(values))
                    columns_str = ", ".join(columns)
                    
                    sql = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
                    cursor.execute(sql, values)
                    
                    op_result = {
                        "type": "insert",
                        "table": table,
                        "rows_affected": cursor.rowcount
                    }
                    total_rows_affected += cursor.rowcount
                
                elif op_type == "update":
                    # Update operation
                    table = op.get("table")
                    where = op.get("where")
                    values = op.get("values")
                    
                    if not table or not where or not values:
                        raise ValueError(f"Operation {idx + 1}: 'table', 'where', and 'values' are required for update type")
                    
                    set_clause = ", ".join([f"{col} = %s" for col in values.keys()])
                    sql = f"UPDATE {table} SET {set_clause} WHERE {where}"
                    cursor.execute(sql, list(values.values()))
                    
                    op_result = {
                        "type": "update",
                        "table": table,
                        "rows_affected": cursor.rowcount
                    }
                    total_rows_affected += cursor.rowcount
                
                elif op_type == "delete":
                    # Delete operation
                    table = op.get("table")
                    where = op.get("where")
                    
                    if not table or not where:
                        raise ValueError(f"Operation {idx + 1}: 'table' and 'where' are required for delete type")
                    
                    sql = f"DELETE FROM {table} WHERE {where}"
                    cursor.execute(sql)
                    
                    op_result = {
                        "type": "delete",
                        "table": table,
                        "rows_affected": cursor.rowcount
                    }
                    total_rows_affected += cursor.rowcount
                
                else:
                    raise ValueError(f"Operation {idx + 1}: Invalid operation type '{op_type}'. Must be 'query', 'insert', 'update', or 'delete'")
                
                results.append(op_result)
            
            # Commit transaction
            conn.commit()
            
            duration_ms = (time.time() - start_time) * 1000
            
            return _format_result(
                status="success",
                operation="execute_transaction",
                rows_affected=total_rows_affected,
                duration_ms=duration_ms,
                result={
                    "isolation_level": isolation_level.upper(),
                    "operations_executed": len(operations),
                    "operation_results": results,
                    "transaction_status": "committed"
                },
                message=f"Transaction completed successfully: {len(operations)} operations executed",
                warnings=warnings
            )
            
        except Exception as e:
            # Rollback on error
            conn.rollback()
            duration_ms = (time.time() - start_time) * 1000
            
            return _format_result(
                status="error",
                operation="execute_transaction",
                duration_ms=duration_ms,
                result={
                    "isolation_level": isolation_level.upper(),
                    "operations_attempted": len(operations),
                    "operations_completed": len(results),
                    "transaction_status": "rolled_back"
                },
                message=f"Transaction rolled back due to error: {str(e)}"
            )
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        return _format_result(
            status="error",
            operation="execute_transaction",
            duration_ms=duration_ms,
            message=f"Failed to execute transaction: {str(e)}"
        )


def backup_table(
    table_name: str,
    backup_name: Optional[str] = None,
    include_indexes: bool = True
) -> Dict:
    """
    Create a backup copy of a table.
    
    Args:
        table_name: Name of the table to backup
        backup_name: Optional custom backup name. If None, uses "backup_<table>_<timestamp>"
        include_indexes: Whether to copy indexes to the backup table
        
    Returns:
        Dictionary with backup results
        
    Examples:
        backup_table("users")
        backup_table("products", backup_name="products_before_migration")
    """
    start_time = time.time()
    warnings = []
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Verify table exists
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = %s
        """, (table_name,))
        
        if cursor.fetchone()[0] == 0:
            return _format_result(
                status="error",
                operation="backup_table",
                message=f"Table '{table_name}' not found"
            )
        
        # Generate backup table name
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{table_name}_{timestamp}"
        
        # Check if backup table already exists
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = %s
        """, (backup_name,))
        
        if cursor.fetchone()[0] > 0:
            return _format_result(
                status="error",
                operation="backup_table",
                message=f"Backup table '{backup_name}' already exists"
            )
        
        # Create backup table with all data
        cursor.execute(f"CREATE TABLE {backup_name} AS SELECT * FROM {table_name}")
        row_count = cursor.rowcount
        
        # Copy indexes if requested
        if include_indexes:
            # Get indexes from original table (excluding primary key)
            cursor.execute("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = %s
                    AND schemaname = 'public'
                    AND indexname NOT LIKE '%_pkey'
            """, (table_name,))
            
            indexes = cursor.fetchall()
            indexes_copied = []
            
            for idx_name, idx_def in indexes:
                try:
                    # Modify index definition to use backup table
                    new_idx_name = idx_name.replace(table_name, backup_name)
                    new_idx_def = idx_def.replace(f" ON {table_name} ", f" ON {backup_name} ")
                    new_idx_def = new_idx_def.replace(f"{idx_name}", f"{new_idx_name}")
                    
                    cursor.execute(new_idx_def)
                    indexes_copied.append(new_idx_name)
                except Exception as e:
                    warnings.append(f"Failed to copy index {idx_name}: {str(e)}")
            
            if indexes_copied:
                warnings.append(f"Copied {len(indexes_copied)} indexes to backup table")
        
        conn.commit()
        
        # Get table sizes
        cursor.execute("""
            SELECT 
                pg_size_pretty(pg_total_relation_size(%s)) as original_size,
                pg_size_pretty(pg_total_relation_size(%s)) as backup_size
        """, (table_name, backup_name))
        
        sizes = cursor.fetchone()
        
        duration_ms = (time.time() - start_time) * 1000
        
        return _format_result(
            status="success",
            operation="backup_table",
            rows_affected=row_count,
            duration_ms=duration_ms,
            result={
                "original_table": table_name,
                "backup_table": backup_name,
                "rows_copied": row_count,
                "original_size": sizes[0] if sizes else "unknown",
                "backup_size": sizes[1] if sizes else "unknown",
                "indexes_copied": include_indexes,
                "restore_sql": f"-- To restore: DROP TABLE {table_name}; ALTER TABLE {backup_name} RENAME TO {table_name};",
                "cleanup_sql": f"DROP TABLE {backup_name};"
            },
            message=f"Table '{table_name}' backed up successfully as '{backup_name}' ({row_count} rows)",
            warnings=warnings
        )
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        return _format_result(
            status="error",
            operation="backup_table",
            duration_ms=duration_ms,
            message=f"Failed to backup table: {str(e)}"
        )
