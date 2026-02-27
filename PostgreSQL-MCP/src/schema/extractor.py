"""
Schema extraction module.
Extracts table structure, columns, keys, and relationships from PostgreSQL.
"""

from typing import Dict, List
from src.database import get_connection


def extract_schema() -> Dict:
    """
    Extract complete PostgreSQL schema including tables, columns, 
    primary keys, and foreign keys.
    
    Returns:
        Dict: Schema with structure:
            {
                "table_name": {
                    "columns": [...],
                    "primary_key": [...],
                    "foreign_keys": [...]
                }
            }
    """
    conn = get_connection()
    cur = conn.cursor()

    # Get all tables
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE';
    """)
    tables = [row[0] for row in cur.fetchall()]

    schema = {}

    for table in tables:
        schema[table] = {
            "columns": [],
            "primary_key": [],
            "foreign_keys": []
        }

        # Extract columns with type and nullability
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = %s;
        """, (table,))
        
        for col_name, data_type, is_nullable in cur.fetchall():
            schema[table]["columns"].append({
                "name": col_name,
                "type": data_type,
                "nullable": is_nullable == "YES"
            })

        # Extract primary keys
        cur.execute("""
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid
                                AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = %s::regclass
            AND i.indisprimary;
        """, (table,))
        schema[table]["primary_key"] = [row[0] for row in cur.fetchall()]

        # Extract foreign keys with nullable info
        cur.execute("""
            SELECT
                kcu.column_name,
                ccu.table_name,
                ccu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu
              ON ccu.constraint_name = tc.constraint_name
            WHERE constraint_type = 'FOREIGN KEY'
              AND tc.table_name=%s;
        """, (table,))

        for col, ref_table, ref_col in cur.fetchall():
            # Get nullable status for FK column
            nullable = next(
                (c["nullable"] for c in schema[table]["columns"] if c["name"] == col),
                True
            )

            schema[table]["foreign_keys"].append({
                "column": col,
                "references_table": ref_table,
                "references_column": ref_col,
                "nullable": nullable
            })

    cur.close()
    conn.close()
    return schema


def get_table_info(table_name: str) -> Dict:
    """
    Get information for a specific table.
    
    Args:
        table_name: Name of the table
        
    Returns:
        Dict: Table information
    """
    schema = extract_schema()
    return schema.get(table_name, {})


def get_tables_list() -> List[str]:
    """
    Get list of all tables in the database.
    
    Returns:
        List[str]: List of table names
    """
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)
    
    tables = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return tables
