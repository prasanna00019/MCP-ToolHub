"""
SchemaIntelligence MCP Server
AI-powered PostgreSQL database analysis and documentation
"""

from mcp.server.fastmcp import FastMCP
from typing import Any, Dict, List, Optional
import json

# Import modular components
from src.schema import extract_schema
from src.analysis import detect_junction_tables, suggest_joins
from src.analysis.detector import detect_implicit_relationships
from src.generation import generate_mermaid_erd, generate_markdown
from src.generation.mermaid_gen import generate_mermaid_flowchart
from src.generation import DiagramRenderer
from src.generation.diagram_renderer import render_database_diagrams as render_diagrams_impl
from src.llm import OllamaAnalyzer

# Import CRUD operations
from src.crud import (
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

# Import Schema Modification operations (Phase 2)
from src.schema_mod import (
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
    schema_drop_view,
)

# Initialize MCP Server
mcp = FastMCP("SchemaIntelligence")


# ============================================
# MCP TOOLS
# ============================================

@mcp.tool()
def analyze_database() -> Dict[str, Any]:
    """
    Analyze PostgreSQL database schema.
    
    Returns comprehensive database analysis including:
    - Schema structure (tables, columns, keys)
    - Junction/association tables
    - Join recommendations
    - ER diagrams in Mermaid format
    - Markdown documentation
    """
    try:
        schema = extract_schema()

        return {
            "status": "success",
            "schema": schema,
            "junction_tables": detect_junction_tables(schema),
            "implicit_relationships": detect_implicit_relationships(schema),
            "suggested_joins": suggest_joins(schema),
            "mermaid_erd": generate_mermaid_erd(schema),
            "mermaid_flowchart": generate_mermaid_flowchart(schema),
            "markdown_documentation": generate_markdown(schema)
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@mcp.tool()
def explain_database() -> Dict[str, Any]:
    """
    Use LLM (Ollama) to generate AI-powered database explanation.
    
    Provides:
    - Business purpose of the database
    - Detected relationships (explicit & implicit)
    - Join type recommendations
    - Improved Mermaid ER diagram
    - Database quality insights
    """
    try:
        schema = extract_schema()
        analyzer = OllamaAnalyzer()
        
        # Check if Ollama is available
        if not analyzer.is_available():
            return {
                "status": "error",
                "error": f"Ollama model '{analyzer.model}' not available at {analyzer.base_url}"
            }
        
        result = analyzer.explain_schema(schema)
        
        return {
            "status": "success",
            "llm_analysis": result
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@mcp.tool()
def get_table_details(table_name: str) -> Dict:
    """
    Get detailed information for a specific table.
    
    Args:
        table_name: Name of the table to analyze
        
    Returns:
        Detailed table structure, relationships, and documentation
    """
    try:
        schema = extract_schema()
        
        if table_name not in schema:
            return {
                "status": "error",
                "error": f"Table '{table_name}' not found"
            }
        
        table_info = schema[table_name]
        
        # Generate documentation for this table
        from src.generation.markdown_gen import generate_table_documentation
        
        return {
            "status": "success",
            "table_name": table_name,
            "info": table_info,
            "documentation": generate_table_documentation(table_name, table_info)
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@mcp.tool()
def list_tables() -> Dict[str, Any]:
    """
    List all tables in the database.
    
    Returns:
        List of table names
    """
    try:
        from src.schema.extractor import get_tables_list
        tables = get_tables_list()
        
        return {
            "status": "success",
            "tables": tables,
            "count": len(tables)
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@mcp.tool()
def check_ollama_status() -> Dict[str, Any]:
    """
    Check if Ollama LLM service is available.
    
    Returns:
        Status of Ollama service and available models
    """
    try:
        analyzer = OllamaAnalyzer()
        models = analyzer.get_available_models()
        
        return {
            "status": "success",
            "ollama_available": True,
            "base_url": analyzer.base_url,
            "configured_model": analyzer.model,
            "available_models": models,
            "model_available": analyzer.model in models
        }
    except Exception as e:
        return {
            "status": "error",
            "ollama_available": False,
            "error": str(e)
        }


@mcp.tool()
def render_database_diagrams(output_format: str = "svg") -> Dict[str, Any]:
    """
    Render database diagrams as SVG images.
    
    Generates visual representations of your database structure including:
    - Entity-Relationship (ER) Diagram: Shows all tables, columns, and relationships
    - Flowchart: Shows table relationships and data flow
    
    Args:
        output_format: Output format (svg recommended; png/pdf may not be supported via API)
        
    Returns:
        Paths to generated SVG diagram files in the 'diagrams/' directory
    """
    try:
        schema = extract_schema()
        diagrams = render_diagrams_impl(
            schema,
            output_dir="diagrams",
            formats=[output_format]
        )
        
        if not diagrams:
            return {
                "status": "warning",
                "message": "Diagrams could not be rendered. Check if mermaid-cli is installed.",
                "installation_hint": "Install mermaid-cli: npm install -g @mermaid-js/mermaid-cli",
                "fallback": "Use analyze_database() for Mermaid syntax instead"
            }
        
        return {
            "status": "success",
            "diagrams": {
                name: str(path) for name, path in diagrams.items()
            },
            "output_format": output_format,
            "message": f"Diagrams rendered successfully in {output_format} format"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


# ============================================
# PHASE 1: CRUD OPERATIONS
# ============================================

# CREATE Operations

@mcp.tool()
def crud_create_record(table_name: str, values: Dict[str, Any]) -> Dict[str, Any]:
    """Insert a single record into a table (parameterized for SQL injection safety)."""
    return create_record(table_name, values)


@mcp.tool()
def crud_create_records_batch(table_name: str, records: List[Dict[str, Any]]) -> Dict:
    """Insert multiple records in a batch (more efficient than single inserts)."""
    return create_records_batch(table_name, records)


@mcp.tool()
def crud_create_table(table_name: str, columns: List[Dict[str, Any]], primary_key: Optional[List[str]] = None) -> Dict:
    """
    Create a new table with specified columns and constraints.
    
    Example columns:
    [
        {"name": "id", "type": "INTEGER", "nullable": False},
        {"name": "name", "type": "VARCHAR(255)", "nullable": False},
        {"name": "email", "type": "VARCHAR(255)", "nullable": True}
    ]
    """
    return create_table(table_name, columns, primary_key)


@mcp.tool()
def crud_create_view(view_name: str, select_query: str, replace_if_exists: bool = False) -> Dict[str, Any]:
    """Create a database view from a SELECT query."""
    return create_view(view_name, select_query, replace_if_exists)


@mcp.tool()
def crud_create_index(index_name: str, table_name: str, columns: List[str], unique: bool = False) -> Dict[str, Any]:
    """Create a single or composite index on table columns."""
    return create_index(index_name, table_name, columns, unique)


# READ Operations

@mcp.tool()
def crud_query_data(query: str, params: Optional[List[Any]] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Dict[str, Any]:
    """
    Execute a SELECT query with optional pagination.
    Use %s for parameterized values: "SELECT * FROM users WHERE age > %s AND city = %s"
    """
    return query_data(query, params, limit, offset)


@mcp.tool()
def crud_get_records(
    table_name: str,
    where_clause: Optional[str] = None,
    where_params: Optional[List[Any]] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    order_by: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get records from a table with filtering and sorting.
    Example: where_clause="age > %s AND city = %s", where_params=[30, "NYC"], order_by="name ASC, age DESC"
    """
    return get_records(table_name, where_clause, where_params, limit, offset, order_by)


@mcp.tool()
def crud_get_record_count(
    table_name: str,
    where_clause: Optional[str] = None,
    where_params: Optional[List[Any]] = None
) -> Dict[str, Any]:
    """Count records in a table with optional filtering."""
    return get_record_count(table_name, where_clause, where_params)


@mcp.tool()
def crud_distinct_values(table_name: str, column_name: str, limit: Optional[int] = None) -> Dict[str, Any]:
    """Get distinct values for a column."""
    return distinct_values(table_name, column_name, limit)


@mcp.tool()
def crud_paginate_data(
    table_name: str,
    page: int = 1,
    page_size: int = 10,
    order_by: Optional[str] = None,
    where_clause: Optional[str] = None,
    where_params: Optional[List[Any]] = None
) -> Dict[str, Any]:
    """Get paginated records from a table with metadata about total pages."""
    return paginate_data(table_name, page, page_size, order_by, where_clause, where_params)


# UPDATE Operations

@mcp.tool()
def crud_update_record(table_name: str, record_id: Any, id_column: str, values: Dict[str, Any]) -> Dict[str, Any]:
    """Update a single record by ID. Example: update_record("users", 123, "id", {"name": "John", "age": 30})"""
    return update_record(table_name, record_id, id_column, values)


@mcp.tool()
def crud_update_records_batch(
    table_name: str,
    where_clause: str,
    where_params: List[Any],
    values: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update multiple records matching a WHERE clause.
    Example: where_clause="age > %s AND city = %s", where_params=[30, "NYC"], values={"status": "active"}
    """
    return update_records_batch(table_name, where_clause, where_params, values)


@mcp.tool()
def crud_update_column(
    table_name: str,
    column_name: str,
    new_value: Any,
    where_clause: Optional[str] = None,
    where_params: Optional[List[Any]] = None
) -> Dict[str, Any]:
    """Bulk update a single column. WARNING: If no WHERE clause, updates ALL records!"""
    return update_column(table_name, column_name, new_value, where_clause, where_params)


@mcp.tool()
def crud_rename_table(old_name: str, new_name: str) -> Dict[str, Any]:
    """Rename a table safely."""
    return rename_table(old_name, new_name)


@mcp.tool()
def crud_rename_column(table_name: str, old_column: str, new_column: str) -> Dict[str, Any]:
    """Rename a column in a table."""
    return rename_column(table_name, old_column, new_column)


# DELETE Operations

@mcp.tool()
def crud_delete_record(table_name: str, record_id: Any, id_column: str) -> Dict[str, Any]:
    """Delete a single record by ID."""
    return delete_record(table_name, record_id, id_column)


@mcp.tool()
def crud_delete_records(table_name: str, where_clause: str, where_params: List[Any]) -> Dict[str, Any]:
    """Delete multiple records matching a WHERE clause."""
    return delete_records(table_name, where_clause, where_params)


@mcp.tool()
def crud_truncate_table(table_name: str) -> Dict[str, Any]:
    """
    Truncate (clear all data from) a table. Much faster than DELETE for large tables.
    WARNING: This deletes all data! Cannot be rolled back in autocommit mode.
    """
    return truncate_table(table_name)


@mcp.tool()
def crud_drop_table(table_name: str, cascade: bool = False) -> Dict[str, Any]:
    """
    Drop (delete) a table from the database.
    WARNING: This is permanent and deletes the entire table structure and data!
    cascade: If True, also drop dependent objects (views, indexes, etc.)
    """
    return drop_table(table_name, cascade)


# ============================================
# PHASE 2: SCHEMA MODIFICATION (DDL)
# ============================================

# --- Column Management ---

@mcp.tool()
def mod_add_column(table_name: str, column: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add a new column to an existing PostgreSQL table (ALTER TABLE ADD COLUMN).
    
    Use this tool when you need to add a column, field, or attribute to a table.
    
    Args:
        table_name: Name of the table to add the column to
        column: Column definition dict with keys:
            - name (str): Column name 
            - type (str): PostgreSQL data type (e.g. VARCHAR(255), INTEGER, TEXT, BOOLEAN, TIMESTAMP)
            - nullable (bool, optional): Whether column allows NULL values. Defaults to True
            
    Example: column = {"name": "status", "type": "VARCHAR(50)", "nullable": false}
    
    Returns:
        Result with status and operation details
    """
    return schema_add_column(table_name, column)


@mcp.tool()
def mod_modify_column_type(table_name: str, column_name: str, new_type: str, using_expression: Optional[str] = None) -> Dict[str, Any]:
    """
    Change/alter/modify the data type of an existing column in a PostgreSQL table (ALTER TABLE ALTER COLUMN TYPE).
    
    Use this tool when you need to change a column's type, convert column types, or alter column definitions.
    
    Args:
        table_name: Name of the table containing the column
        column_name: Name of the column to modify
        new_type: New PostgreSQL data type (e.g. TEXT, INTEGER, BIGINT, DECIMAL(10,2), BOOLEAN)
        using_expression: Optional USING clause for type conversion (e.g. "column_name::integer").
                          Required when PostgreSQL cannot automatically cast between the old and new types.
    
    Returns:
        Result with status and operation details
    """
    return schema_modify_column_type(table_name, column_name, new_type, using_expression)


@mcp.tool()
def mod_drop_column(table_name: str, column_name: str, cascade: bool = False) -> Dict[str, Any]:
    """
    Drop/remove/delete a column from an existing PostgreSQL table (ALTER TABLE DROP COLUMN).
    
    Use this tool when you need to remove a column or field from a table.
    WARNING: This permanently deletes the column and all its data.
    
    Args:
        table_name: Name of the table
        column_name: Name of the column to drop
        cascade: If True, also drop objects that depend on this column (views, constraints, etc.)
    
    Returns:
        Result with status and operation details
    """
    return schema_drop_column(table_name, column_name, cascade)


@mcp.tool()
def mod_set_column_nullable(table_name: str, column_name: str, is_nullable: bool) -> Dict[str, Any]:
    """
    Set or drop the NOT NULL constraint on a column (ALTER TABLE ALTER COLUMN SET/DROP NOT NULL).
    
    Use this tool to make a column nullable or not nullable, toggle null constraints.
    
    Args:
        table_name: Name of the table
        column_name: Name of the column
        is_nullable: True to allow NULLs (DROP NOT NULL), False to disallow NULLs (SET NOT NULL)
    
    Returns:
        Result with status and operation details
    """
    return schema_set_column_nullable(table_name, column_name, is_nullable)


# --- Index Operations ---

@mcp.tool()
def mod_list_indexes(table_name: Optional[str] = None) -> Dict[str, Any]:
    """
    List all indexes in the PostgreSQL database, optionally filtered by table name.
    
    Use this tool to see what indexes exist, check index definitions, or audit database indexes.
    
    Args:
        table_name: Optional table name to filter indexes for a specific table
    
    Returns:
        Result with list of indexes including schema, table, index name, and definition
    """
    return schema_list_indexes(table_name)


@mcp.tool()
def mod_drop_index(index_name: str, cascade: bool = False) -> Dict[str, Any]:
    """
    Drop/remove/delete an index from the PostgreSQL database (DROP INDEX).
    
    Use this tool to remove an index that is no longer needed.
    
    Args:
        index_name: Name of the index to drop
        cascade: If True, also drop objects that depend on this index
    
    Returns:
        Result with status and operation details
    """
    return schema_drop_index(index_name, cascade)


# --- Constraint Operations ---

@mcp.tool()
def mod_list_constraints(table_name: Optional[str] = None) -> Dict[str, Any]:
    """
    List all constraints in the PostgreSQL database (Primary Keys, Foreign Keys, Check, Unique constraints).
    
    Use this tool to see what constraints exist on tables, audit relationships, or check constraint definitions.
    
    Args:
        table_name: Optional table name to filter constraints for a specific table
    
    Returns:
        Result with list of constraints including name, type, table, and definition
    """
    return schema_list_constraints(table_name)


@mcp.tool()
def mod_add_primary_key(table_name: str, columns: List[str], constraint_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Add a primary key constraint to a PostgreSQL table (ALTER TABLE ADD PRIMARY KEY).
    
    Use this tool to define or add a primary key on one or more columns.
    
    Args:
        table_name: Name of the table
        columns: List of column names for the primary key (e.g. ["id"] or ["col1", "col2"] for composite)
        constraint_name: Optional custom name for the constraint (e.g. "pk_users")
    
    Returns:
        Result with status and operation details
    """
    return schema_add_primary_key(table_name, columns, constraint_name)


@mcp.tool()
def mod_add_foreign_key(
    table_name: str, 
    columns: List[str], 
    ref_table: str, 
    ref_columns: List[str], 
    constraint_name: Optional[str] = None, 
    on_delete: str = 'NO ACTION'
) -> Dict[str, Any]:
    """
    Add a foreign key constraint linking columns in one table to columns in another (ALTER TABLE ADD FOREIGN KEY).
    
    Use this tool to create relationships between tables, enforce referential integrity, or link tables with FK.
    
    Args:
        table_name: Name of the table to add the foreign key to
        columns: List of column names in this table (e.g. ["user_id"])
        ref_table: Name of the referenced/target table (e.g. "users")
        ref_columns: List of referenced column names (e.g. ["id"])
        constraint_name: Optional custom name for the constraint (e.g. "fk_orders_user_id")
        on_delete: Action on delete - CASCADE, RESTRICT, SET NULL, SET DEFAULT, or NO ACTION
    
    Returns:
        Result with status and operation details
    """
    return schema_add_foreign_key(table_name, columns, ref_table, ref_columns, constraint_name, on_delete)


@mcp.tool()
def mod_drop_constraint(table_name: str, constraint_name: str, cascade: bool = False) -> Dict[str, Any]:
    """
    Drop/remove a constraint from a PostgreSQL table (ALTER TABLE DROP CONSTRAINT).
    
    Use this tool to remove primary keys, foreign keys, unique constraints, or check constraints.
    
    Args:
        table_name: Name of the table
        constraint_name: Name of the constraint to drop
        cascade: If True, also drop objects that depend on this constraint
    
    Returns:
        Result with status and operation details
    """
    return schema_drop_constraint(table_name, constraint_name, cascade)


# --- View Management ---

@mcp.tool()
def mod_list_views() -> Dict[str, Any]:
    """
    List all user-defined views in the PostgreSQL database.
    
    Use this tool to see what views exist, enumerate virtual tables.
    
    Returns:
        Result with list of view names
    """
    return schema_list_views()


@mcp.tool()
def mod_get_view_definition(view_name: str) -> Dict[str, Any]:
    """
    Get the underlying SQL SELECT query definition of a PostgreSQL view.
    
    Use this tool to inspect what SQL a view uses, see view source code, or understand view logic.
    
    Args:
        view_name: Name of the view to inspect
    
    Returns:
        Result with view name and its SQL definition
    """
    return schema_get_view_definition(view_name)


@mcp.tool()
def mod_drop_view(view_name: str, cascade: bool = False) -> Dict[str, Any]:
    """
    Drop/remove/delete a view from the PostgreSQL database (DROP VIEW).
    
    Use this tool to remove a view that is no longer needed.
    
    Args:
        view_name: Name of the view to drop
        cascade: If True, also drop objects that depend on this view
    
    Returns:
        Result with status and operation details
    """
    return schema_drop_view(view_name, cascade)


if __name__ == "__main__":
    mcp.run()
