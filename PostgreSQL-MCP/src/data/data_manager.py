"""
Data Manager: Import/Export, Search, and Data Quality tools.
Phase 4A: export_data, import_data
Phase 4B: search_data, find_duplicates, validate_foreign_keys
"""

import time
import csv
import json
import os
from typing import Dict, List, Optional, Any, Union
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


# ============================================
# PHASE 4A: IMPORT/EXPORT
# ============================================

def export_data(
    table_name: str,
    format: str = "json",
    where_clause: Optional[str] = None,
    output_path: Optional[str] = None,
    limit: Optional[int] = None
) -> Dict:
    """
    Export table data to CSV, JSON, or SQL format.
    
    Args:
        table_name: Name of the table to export
        format: Export format - 'csv', 'json', or 'sql'
        where_clause: Optional WHERE clause to filter data (without 'WHERE' keyword)
        output_path: Optional file path to save output. If None, returns data as string
        limit: Optional row limit for export
        
    Returns:
        Dictionary with export results
        
    Examples:
        export_data("products", format="csv", where_clause="price > 100")
        export_data("users", format="json", output_path="users.json")
        export_data("orders", format="sql", where_clause="status = 'pending'")
    """
    start_time = time.time()
    warnings = []
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Validate format
        valid_formats = ["csv", "json", "sql"]
        if format.lower() not in valid_formats:
            return _format_result(
                status="error",
                operation="export_data",
                message=f"Invalid format '{format}'. Must be one of: {', '.join(valid_formats)}"
            )
        
        # Build query
        query = f"SELECT * FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        if not rows:
            return _format_result(
                status="success",
                operation="export_data",
                duration_ms=(time.time() - start_time) * 1000,
                message="No data found to export",
                warnings=["Query returned no rows"]
            )
        
        # Export based on format
        if format.lower() == "csv":
            output = _export_to_csv(columns, rows, output_path)
        elif format.lower() == "json":
            output = _export_to_json(columns, rows, output_path)
        elif format.lower() == "sql":
            output = _export_to_sql(table_name, columns, rows, output_path)
        
        duration_ms = (time.time() - start_time) * 1000
        
        result = {
            "table": table_name,
            "format": format,
            "rows_exported": len(rows),
            "columns": columns
        }
        
        if output_path:
            result["file_path"] = output_path
            result["file_size_bytes"] = os.path.getsize(output_path) if os.path.exists(output_path) else 0
            message = f"Exported {len(rows)} rows to {output_path}"
        else:
            result["data"] = output
            message = f"Exported {len(rows)} rows as {format}"
        
        return _format_result(
            status="success",
            operation="export_data",
            rows_affected=len(rows),
            duration_ms=duration_ms,
            result=result,
            message=message,
            warnings=warnings
        )
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        return _format_result(
            status="error",
            operation="export_data",
            duration_ms=duration_ms,
            message=f"Failed to export data: {str(e)}"
        )


def _export_to_csv(columns: List[str], rows: List[tuple], output_path: Optional[str]) -> str:
    """Helper function to export data to CSV format."""
    if output_path:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(rows)
        return output_path
    else:
        # Return CSV as string
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        writer.writerows(rows)
        return output.getvalue()


def _export_to_json(columns: List[str], rows: List[tuple], output_path: Optional[str]) -> Union[str, List[Dict]]:
    """Helper function to export data to JSON format."""
    data = [dict(zip(columns, row)) for row in rows]
    
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        return output_path
    else:
        return data


def _export_to_sql(table_name: str, columns: List[str], rows: List[tuple], output_path: Optional[str]) -> str:
    """Helper function to export data to SQL INSERT statements."""
    sql_statements = []
    
    for row in rows:
        # Format values properly for SQL
        formatted_values = []
        for val in row:
            if val is None:
                formatted_values.append("NULL")
            elif isinstance(val, str):
                # Escape single quotes
                escaped = val.replace("'", "''")
                formatted_values.append(f"'{escaped}'")
            elif isinstance(val, (int, float)):
                formatted_values.append(str(val))
            else:
                formatted_values.append(f"'{str(val)}'")
        
        values_str = ", ".join(formatted_values)
        columns_str = ", ".join(columns)
        sql_statements.append(f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_str});")
    
    output = "\n".join(sql_statements)
    
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output)
        return output_path
    else:
        return output


def import_data(
    table_name: str,
    format: str,
    source: str,
    mapping: Optional[Dict[str, str]] = None,
    conflict_resolution: str = "error"
) -> Dict:
    """
    Import data from CSV or JSON into a table.
    
    Args:
        table_name: Target table name
        format: Source format - 'csv' or 'json'
        source: File path or JSON string
        mapping: Optional column mapping {source_col: target_col}
        conflict_resolution: How to handle conflicts - 'error', 'skip', or 'upsert'
        
    Returns:
        Dictionary with import results
        
    Examples:
        import_data("products", "csv", "products.csv")
        import_data("users", "json", '[{"name": "John", "email": "john@example.com"}]')
    """
    start_time = time.time()
    warnings = []
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Validate format
        valid_formats = ["csv", "json"]
        if format.lower() not in valid_formats:
            return _format_result(
                status="error",
                operation="import_data",
                message=f"Invalid format '{format}'. Must be one of: {', '.join(valid_formats)}"
            )
        
        # Validate conflict resolution
        valid_conflicts = ["error", "skip", "upsert"]
        if conflict_resolution.lower() not in valid_conflicts:
            return _format_result(
                status="error",
                operation="import_data",
                message=f"Invalid conflict_resolution '{conflict_resolution}'. Must be one of: {', '.join(valid_conflicts)}"
            )
        
        # Get table columns
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
        """, (table_name,))
        
        table_columns = {row[0]: row[1] for row in cursor.fetchall()}
        
        if not table_columns:
            return _format_result(
                status="error",
                operation="import_data",
                message=f"Table '{table_name}' not found"
            )
        
        # Parse source data
        if format.lower() == "csv":
            data = _parse_csv(source)
        else:  # json
            data = _parse_json(source)
        
        if not data:
            return _format_result(
                status="success",
                operation="import_data",
                message="No data found to import",
                warnings=["Source contains no data rows"]
            )
        
        # Apply column mapping
        if mapping:
            data = _apply_column_mapping(data, mapping)
        
        # Validate columns
        source_columns = set(data[0].keys())
        target_columns = set(table_columns.keys())
        
        # Warn about unmapped columns
        unmapped = source_columns - target_columns
        if unmapped:
            warnings.append(f"Source columns not in target table: {', '.join(unmapped)}")
        
        # Import data
        success_count = 0
        error_count = 0
        errors = []
        
        for idx, row_data in enumerate(data):
            try:
                # Filter to only columns that exist in table
                filtered_data = {k: v for k, v in row_data.items() if k in target_columns}
                
                if not filtered_data:
                    error_count += 1
                    errors.append(f"Row {idx + 1}: No valid columns to insert")
                    continue
                
                columns = list(filtered_data.keys())
                values = list(filtered_data.values())
                
                placeholders = ", ".join(["%s"] * len(values))
                columns_str = ", ".join(columns)
                
                if conflict_resolution == "skip":
                    # Try insert, ignore conflicts
                    insert_sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
                elif conflict_resolution == "upsert":
                    # Get primary key
                    cursor.execute("""
                        SELECT a.attname
                        FROM pg_index i
                        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                        WHERE i.indrelid = %s::regclass AND i.indisprimary
                    """, (table_name,))
                    pk_cols = [row[0] for row in cursor.fetchall()]
                    
                    if pk_cols:
                        update_cols = [f"{col} = EXCLUDED.{col}" for col in columns if col not in pk_cols]
                        update_str = ", ".join(update_cols) if update_cols else columns_str + " = EXCLUDED." + columns_str
                        insert_sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders}) ON CONFLICT ({', '.join(pk_cols)}) DO UPDATE SET {update_str}"
                    else:
                        warnings.append(f"Table has no primary key, using skip strategy instead of upsert")
                        insert_sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
                else:
                    # error mode - normal insert
                    insert_sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
                
                cursor.execute(insert_sql, values)
                success_count += 1
                
            except Exception as e:
                error_count += 1
                if len(errors) < 10:  # Limit error messages
                    errors.append(f"Row {idx + 1}: {str(e)}")
        
        conn.commit()
        
        duration_ms = (time.time() - start_time) * 1000
        
        if errors and len(errors) == 10:
            errors.append(f"... and {error_count - 10} more errors")
        
        return _format_result(
            status="success" if error_count == 0 else "warning",
            operation="import_data",
            rows_affected=success_count,
            duration_ms=duration_ms,
            result={
                "table": table_name,
                "format": format,
                "rows_processed": len(data),
                "rows_imported": success_count,
                "rows_failed": error_count,
                "errors": errors[:10] if errors else []
            },
            message=f"Imported {success_count}/{len(data)} rows successfully",
            warnings=warnings
        )
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        return _format_result(
            status="error",
            operation="import_data",
            duration_ms=duration_ms,
            message=f"Failed to import data: {str(e)}"
        )


def _parse_csv(source: str) -> List[Dict]:
    """Parse CSV from file path or string."""
    if os.path.exists(source):
        # Read from file
        with open(source, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    else:
        # Parse as CSV string
        import io
        reader = csv.DictReader(io.StringIO(source))
        return list(reader)


def _parse_json(source: str) -> List[Dict]:
    """Parse JSON from file path or string."""
    if os.path.exists(source):
        # Read from file
        with open(source, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        # Parse as JSON string
        data = json.loads(source)
    
    # Ensure data is a list of dictionaries
    if isinstance(data, dict):
        data = [data]
    
    return data


def _apply_column_mapping(data: List[Dict], mapping: Dict[str, str]) -> List[Dict]:
    """Apply column name mapping to data."""
    mapped_data = []
    for row in data:
        mapped_row = {}
        for source_col, target_col in mapping.items():
            if source_col in row:
                mapped_row[target_col] = row[source_col]
        # Include unmapped columns as-is
        for col, val in row.items():
            if col not in mapping:
                mapped_row[col] = val
        mapped_data.append(mapped_row)
    return mapped_data


# ============================================
# PHASE 4B: DATA QUALITY
# ============================================

def search_data(
    table_name: str,
    search_columns: List[str],
    search_term: str,
    search_type: str = "ilike",
    limit: int = 100
) -> Dict:
    """
    Search for data using various search strategies.
    
    Args:
        table_name: Table to search in
        search_columns: Columns to search
        search_term: Term to search for
        search_type: 'ilike' (case-insensitive), 'like' (case-sensitive), or 'similarity' (fuzzy)
        limit: Maximum number of results
        
    Returns:
        Dictionary with search results
        
    Examples:
        search_data("products", ["name", "description"], "laptop", search_type="ilike")
        search_data("users", ["email"], "john", search_type="similarity")
    """
    start_time = time.time()
    warnings = []
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Validate search type
        valid_types = ["ilike", "like", "similarity"]
        if search_type.lower() not in valid_types:
            return _format_result(
                status="error",
                operation="search_data",
                message=f"Invalid search_type '{search_type}'. Must be one of: {', '.join(valid_types)}"
            )
        
        # Verify table exists
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
        """, (table_name,))
        
        available_columns = {row[0] for row in cursor.fetchall()}
        
        if not available_columns:
            return _format_result(
                status="error",
                operation="search_data",
                message=f"Table '{table_name}' not found"
            )
        
        # Validate search columns
        invalid_columns = set(search_columns) - available_columns
        if invalid_columns:
            return _format_result(
                status="error",
                operation="search_data",
                message=f"Invalid columns: {', '.join(invalid_columns)}"
            )
        
        # Build search query based on type
        if search_type.lower() == "similarity":
            # Enable pg_trgm extension if available
            try:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
                conn.commit()
            except:
                warnings.append("pg_trgm extension not available, falling back to ILIKE search")
                search_type = "ilike"
        
        if search_type.lower() == "similarity":
            # Use trigram similarity
            conditions = [f"similarity({col}, %s) > 0.3" for col in search_columns]
            where_clause = " OR ".join(conditions)
            order_by = f"GREATEST({', '.join([f'similarity({col}, %s)' for col in search_columns])}) DESC"
            params = [search_term] * len(search_columns) + [search_term] * len(search_columns)
            
            query = f"""
                SELECT *, GREATEST({', '.join([f'similarity({col}, %s)' for col in search_columns])}) as relevance
                FROM {table_name}
                WHERE {where_clause}
                ORDER BY {order_by}
                LIMIT %s
            """
            params = [search_term] * (len(search_columns) * 3) + [limit]
        else:
            # Use LIKE or ILIKE
            operator = "ILIKE" if search_type.lower() == "ilike" else "LIKE"
            search_pattern = f"%{search_term}%"
            conditions = [f"{col}::text {operator} %s" for col in search_columns]
            where_clause = " OR ".join(conditions)
            params = [search_pattern] * len(search_columns) + [limit]
            
            query = f"""
                SELECT *
                FROM {table_name}
                WHERE {where_clause}
                LIMIT %s
            """
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        results = [dict(zip(columns, row)) for row in rows]
        
        duration_ms = (time.time() - start_time) * 1000
        
        return _format_result(
            status="success",
            operation="search_data",
            rows_affected=len(results),
            duration_ms=duration_ms,
            result={
                "table": table_name,
                "search_columns": search_columns,
                "search_term": search_term,
                "search_type": search_type,
                "results": results,
                "result_count": len(results)
            },
            message=f"Found {len(results)} matching rows",
            warnings=warnings
        )
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        return _format_result(
            status="error",
            operation="search_data",
            duration_ms=duration_ms,
            message=f"Failed to search data: {str(e)}"
        )

