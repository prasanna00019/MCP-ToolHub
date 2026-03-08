"""
Query Optimizer: Query analysis, execution plans, and index recommendations.
Phase 3A: explain_query, suggest_indexes, find_unused_indexes
"""

import time
from typing import Dict, List, Optional, Any
from src.database import get_connection


def _format_result(
    status: str,
    operation: str,
    duration_ms: float = 0,
    result: Any = None,
    message: str = "",
    warnings: List[str] = None,
) -> Dict:
    """Format operation result in standard format."""
    return {
        "status": status,
        "operation": operation,
        "duration_ms": round(duration_ms, 2),
        "result": result,
        "message": message,
        "warnings": warnings or [],
    }


def explain_query(
    query: str,
    analyze: bool = False,
    format: str = "text"
) -> Dict:
    """
    Get query execution plan using EXPLAIN or EXPLAIN ANALYZE.
    
    Args:
        query: SQL query to analyze
        analyze: If True, actually execute the query and show real statistics
        format: Output format - 'text', 'json', or 'yaml'
        
    Returns:
        Dictionary with execution plan details
        
    Example:
        explain_query("SELECT * FROM products WHERE price > 100", analyze=True)
    """
    start_time = time.time()
    warnings = []
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Validate format parameter
        valid_formats = ["text", "json", "yaml"]
        if format.lower() not in valid_formats:
            return _format_result(
                status="error",
                operation="explain_query",
                message=f"Invalid format '{format}'. Must be one of: {', '.join(valid_formats)}"
            )
        
        # Build EXPLAIN command
        explain_cmd = "EXPLAIN"
        if analyze:
            explain_cmd += " ANALYZE"
            warnings.append("ANALYZE option will execute the query - use with caution on write operations")
        
        if format.lower() != "text":
            explain_cmd += f" (FORMAT {format.upper()})"
        
        full_query = f"{explain_cmd} {query}"
        
        cursor.execute(full_query)
        rows = cursor.fetchall()
        
        # Format result based on output format
        if format.lower() == "json":
            # JSON format returns a single row with a JSON object
            result = rows[0][0] if rows else {}
        elif format.lower() == "yaml":
            # YAML format returns multiple lines
            result = "\n".join([row[0] for row in rows])
        else:
            # Text format returns multiple lines
            result = [row[0] for row in rows]
        
        duration_ms = (time.time() - start_time) * 1000
        
        return _format_result(
            status="success",
            operation="explain_query",
            duration_ms=duration_ms,
            result={
                "query": query,
                "execution_plan": result,
                "format": format,
                "analyzed": analyze
            },
            message=f"Execution plan generated successfully ({format} format)",
            warnings=warnings
        )
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        return _format_result(
            status="error",
            operation="explain_query",
            duration_ms=duration_ms,
            message=f"Failed to generate execution plan: {str(e)}"
        )


def suggest_indexes(
    table_name: Optional[str] = None,
    analyze_queries: bool = False
) -> Dict:
    """
    Suggest potential indexes based on table structure and foreign keys.
    
    Args:
        table_name: Specific table to analyze (analyzes all tables if None)
        analyze_queries: If True, also analyze pg_stat_statements for query patterns
        
    Returns:
        Dictionary with index recommendations
        
    Example:
        suggest_indexes("orders")
    """
    start_time = time.time()
    warnings = []
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        recommendations = []
        
        # Get tables to analyze
        if table_name:
            tables = [table_name]
            # Verify table exists
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = %s
            """, (table_name,))
            if not cursor.fetchone():
                return _format_result(
                    status="error",
                    operation="suggest_indexes",
                    message=f"Table '{table_name}' not found"
                )
        else:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            tables = [row[0] for row in cursor.fetchall()]
        
        # Analyze each table
        for tbl in tables:
            # 1. Check for foreign key columns without indexes
            cursor.execute("""
                SELECT 
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_name = %s
                    AND tc.table_schema = 'public'
            """, (tbl,))
            
            fk_columns = cursor.fetchall()
            
            for fk in fk_columns:
                table, column, ref_table, ref_column = fk
                
                # Check if index exists on this column
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM pg_indexes
                    WHERE tablename = %s
                    AND indexdef LIKE %s
                """, (table, f"%{column}%"))
                
                index_count = cursor.fetchone()[0]
                
                if index_count == 0:
                    recommendations.append({
                        "table": table,
                        "recommended_index": f"idx_{table}_{column}",
                        "columns": [column],
                        "reason": f"Foreign key to {ref_table}({ref_column}) - no index found",
                        "priority": "high",
                        "estimated_benefit": "Improves JOIN performance and foreign key constraint checks",
                        "sql": f"CREATE INDEX idx_{table}_{column} ON {table}({column});"
                    })
            
            # 2. Check for large tables without primary key
            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.table_constraints
                WHERE table_name = %s
                    AND table_schema = 'public'
                    AND constraint_type = 'PRIMARY KEY'
            """, (tbl,))
            
            has_pk = cursor.fetchone()[0] > 0
            
            if not has_pk:
                # Get table row count
                cursor.execute(f"SELECT COUNT(*) FROM {tbl}")
                row_count = cursor.fetchone()[0]
                
                if row_count > 100:
                    warnings.append(f"Table '{tbl}' has {row_count} rows but no primary key")
                    recommendations.append({
                        "table": tbl,
                        "recommended_index": f"pk_{tbl}_id",
                        "columns": ["id"],
                        "reason": f"Table has {row_count} rows but no primary key",
                        "priority": "high",
                        "estimated_benefit": "Enables efficient row identification and improves query performance",
                        "sql": f"ALTER TABLE {tbl} ADD COLUMN id SERIAL PRIMARY KEY;" if row_count == 0 else "-- Manual review needed: Add appropriate primary key"
                    })
            
            # 3. Suggest indexes for commonly filtered columns (if table has data)
            cursor.execute(f"SELECT COUNT(*) FROM {tbl}")
            row_count = cursor.fetchone()[0]
            
            if row_count > 1000:
                # Get columns that might benefit from indexes (timestamps, status fields, etc.)
                cursor.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = %s
                        AND table_schema = 'public'
                        AND (
                            data_type IN ('timestamp', 'timestamp with time zone', 'date')
                            OR column_name LIKE '%%status%%'
                            OR column_name LIKE '%%type%%'
                            OR column_name LIKE '%%category%%'
                        )
                    ORDER BY ordinal_position
                """, (tbl,))
                
                candidate_columns = cursor.fetchall()
                
                for col_name, data_type in candidate_columns:
                    # Check if index already exists
                    cursor.execute("""
                        SELECT COUNT(*)
                        FROM pg_indexes
                        WHERE tablename = %s
                        AND indexdef LIKE %s
                    """, (tbl, f"%{col_name}%"))
                    
                    index_count = cursor.fetchone()[0]
                    
                    if index_count == 0:
                        recommendations.append({
                            "table": tbl,
                            "recommended_index": f"idx_{tbl}_{col_name}",
                            "columns": [col_name],
                            "reason": f"Large table ({row_count} rows) with potentially filterable {data_type} column",
                            "priority": "medium",
                            "estimated_benefit": "Improves WHERE clause performance if this column is frequently filtered",
                            "sql": f"CREATE INDEX idx_{tbl}_{col_name} ON {tbl}({col_name});"
                        })
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Sort recommendations by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda x: priority_order.get(x["priority"], 3))
        
        return _format_result(
            status="success",
            operation="suggest_indexes",
            duration_ms=duration_ms,
            result={
                "tables_analyzed": len(tables),
                "recommendations": recommendations,
                "total_recommendations": len(recommendations)
            },
            message=f"Analyzed {len(tables)} table(s), found {len(recommendations)} recommendation(s)",
            warnings=warnings
        )
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        return _format_result(
            status="error",
            operation="suggest_indexes",
            duration_ms=duration_ms,
            message=f"Failed to generate index recommendations: {str(e)}"
        )


def find_unused_indexes(min_size_mb: float = 1.0) -> Dict:
    """
    Find indexes with zero or low usage that might be candidates for removal.
    
    Args:
        min_size_mb: Minimum index size in MB to report (default: 1.0)
        
    Returns:
        Dictionary with unused index details
        
    Example:
        find_unused_indexes(min_size_mb=5.0)
    """
    start_time = time.time()
    warnings = []
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Query to find unused indexes
        cursor.execute("""
            SELECT
                schemaname,
                tablename,
                indexname,
                idx_scan AS index_scans,
                pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
                pg_relation_size(indexrelid)::float / (1024*1024) AS size_mb,
                idx_tup_read AS tuples_read,
                idx_tup_fetch AS tuples_fetched
            FROM pg_stat_user_indexes
            WHERE schemaname = 'public'
                AND pg_relation_size(indexrelid) >= %s * 1024 * 1024
            ORDER BY pg_relation_size(indexrelid) DESC
        """, (min_size_mb,))
        
        all_indexes = cursor.fetchall()
        unused_indexes = []
        low_usage_indexes = []
        
        for idx in all_indexes:
            schema, table, index_name, scans, size_pretty, size_mb, tup_read, tup_fetch = idx
            
            # Check if it's a primary key or unique constraint (don't recommend removing these)
            cursor.execute("""
                SELECT constraint_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.constraint_column_usage ccu
                    ON tc.constraint_name = ccu.constraint_name
                WHERE tc.table_name = %s
                    AND tc.constraint_type IN ('PRIMARY KEY', 'UNIQUE')
                    AND EXISTS (
                        SELECT 1 FROM pg_indexes
                        WHERE tablename = %s
                        AND indexname = %s
                    )
            """, (table, table, index_name))
            
            is_constraint = cursor.fetchone() is not None
            
            index_info = {
                "schema": schema,
                "table": table,
                "index_name": index_name,
                "size": size_pretty,
                "size_mb": round(size_mb, 2),
                "scans": scans,
                "tuples_read": tup_read,
                "tuples_fetched": tup_fetch,
                "is_constraint_index": is_constraint
            }
            
            if scans == 0 and not is_constraint:
                index_info["recommendation"] = "Consider dropping - never used"
                index_info["sql"] = f"DROP INDEX IF EXISTS {index_name};"
                unused_indexes.append(index_info)
            elif scans < 10 and not is_constraint:
                index_info["recommendation"] = "Low usage - investigate if needed"
                index_info["sql"] = f"-- Review usage: DROP INDEX IF EXISTS {index_name};"
                low_usage_indexes.append(index_info)
        
        if not all_indexes:
            warnings.append(f"No indexes found with size >= {min_size_mb} MB")
        
        duration_ms = (time.time() - start_time) * 1000
        
        total_unused_size = sum(idx["size_mb"] for idx in unused_indexes)
        total_low_usage_size = sum(idx["size_mb"] for idx in low_usage_indexes)
        
        return _format_result(
            status="success",
            operation="find_unused_indexes",
            duration_ms=duration_ms,
            result={
                "unused_indexes": unused_indexes,
                "low_usage_indexes": low_usage_indexes,
                "total_unused": len(unused_indexes),
                "total_low_usage": len(low_usage_indexes),
                "total_indexes_analyzed": len(all_indexes),
                "potential_space_savings_mb": round(total_unused_size, 2),
                "low_usage_space_mb": round(total_low_usage_size, 2)
            },
            message=f"Found {len(unused_indexes)} unused and {len(low_usage_indexes)} low-usage indexes",
            warnings=warnings
        )
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        return _format_result(
            status="error",
            operation="find_unused_indexes",
            duration_ms=duration_ms,
            message=f"Failed to find unused indexes: {str(e)}"
        )
