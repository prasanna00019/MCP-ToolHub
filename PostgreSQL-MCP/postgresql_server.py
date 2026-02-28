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


if __name__ == "__main__":
    mcp.run()
