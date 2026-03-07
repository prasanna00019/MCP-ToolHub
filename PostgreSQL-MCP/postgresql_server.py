"""
SchemaIntelligence MCP Server (Optimized Edition)
AI-powered PostgreSQL database analysis and documentation
Reduced from 38 tools to 18 tools for better performance and lower token usage
"""

from mcp.server.fastmcp import FastMCP
from typing import Any, Dict, List, Optional, Union
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

# Import Schema Modification operations
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
# CATEGORY 1: ANALYSIS & SCHEMA TOOLS (4 tools)
# ============================================

@mcp.tool()
def analyze_database() -> Dict[str, Any]:
    """
    Analyze PostgreSQL database schema comprehensively.
    
    Returns complete database analysis including:
    - Schema structure (tables, columns, keys, data types)
    - Junction/association tables detection
    - Join recommendations (INNER vs LEFT)
    - ER diagrams in Mermaid format
    - Relationship flowcharts
    - Comprehensive Markdown documentation
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
def get_database_info(info_type: str = "tables") -> Dict[str, Any]:
    """
    Get various types of database information (unified info retrieval).
    
    Args:
        info_type: Type of information to retrieve:
            - "tables": List all tables in the database
            - "ollama": Check Ollama LLM service status and available models
            - "summary": Quick database statistics (table count, total size)
            
    Returns:
        Requested database information
    """
    try:
        if info_type == "tables":
            from src.schema.extractor import get_tables_list
            tables = get_tables_list()
            return {
                "status": "success",
                "info_type": "tables",
                "tables": tables,
                "count": len(tables)
            }
            
        elif info_type == "ollama":
            analyzer = OllamaAnalyzer()
            models = analyzer.get_available_models()
            return {
                "status": "success",
                "info_type": "ollama",
                "ollama_available": True,
                "base_url": analyzer.base_url,
                "configured_model": analyzer.model,
                "available_models": models,
                "model_available": analyzer.model in models
            }
            
        elif info_type == "summary":
            from src.schema.extractor import get_tables_list
            tables = get_tables_list()
            return {
                "status": "success",
                "info_type": "summary",
                "table_count": len(tables),
                "tables": tables
            }
            
        else:
            return {
                "status": "error",
                "error": f"Unknown info_type: '{info_type}'. Valid options: 'tables', 'ollama', 'summary'"
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@mcp.tool()
def render_database_diagrams(output_format: str = "svg") -> Dict[str, Any]:
    """
    Render database diagrams as visual images (SVG/PNG/PDF).
    
    Generates visual representations of your database structure:
    - Entity-Relationship (ER) Diagram: Shows all tables, columns, and relationships
    - Flowchart: Shows table relationships and data flow
    
    Args:
        output_format: Output format (svg recommended; png/pdf require mermaid-cli)
        
    Returns:
        Paths to generated diagram files in the 'diagrams/' directory
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
# CATEGORY 2: CRUD CREATE OPERATIONS (3 tools)
# ============================================

@mcp.tool()
def crud_insert(table_name: str, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Insert records into a table (supports single or batch inserts).
    
    Automatically detects single vs batch insert:
    - If data is Dict: Inserts a single record
    - If data is List[Dict]: Batch inserts multiple records
    
    Args:
        table_name: Name of the table to insert into
        data: Single record (Dict) or multiple records (List[Dict])
              Example single: {"name": "John", "age": 30}
              Example batch: [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]
    
    Returns:
        Result with status, inserted count, and operation details
    """
    try:
        if isinstance(data, dict):
            # Single record insert
            return create_record(table_name, data)
        elif isinstance(data, list):
            # Batch insert
            return create_records_batch(table_name, data)
        else:
            return {
                "status": "error",
                "error": "data must be a Dict (single record) or List[Dict] (batch insert)"
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@mcp.tool()
def crud_create_table(table_name: str, columns: List[Dict[str, Any]], primary_key: Optional[List[str]] = None) -> Dict:
    """
    Create a new table with specified columns and constraints.
    
    Args:
        table_name: Name of the new table
        columns: List of column definitions, each with:
            - name (str): Column name 
            - type (str): PostgreSQL data type (INTEGER, VARCHAR(n), TEXT, BOOLEAN, TIMESTAMP, etc.)
            - nullable (bool, optional): Whether column allows NULL values (default: True)
        primary_key: Optional list of column names to form the primary key
        
    Example:
        columns = [
            {"name": "id", "type": "INTEGER", "nullable": False},
            {"name": "name", "type": "VARCHAR(255)", "nullable": False},
            {"name": "email", "type": "VARCHAR(255)", "nullable": True}
        ]
        primary_key = ["id"]
    
    Returns:
        Result with status and operation details
    """
    return create_table(table_name, columns, primary_key)


@mcp.tool()
def crud_create_view(view_name: str, select_query: str, replace_if_exists: bool = False) -> Dict[str, Any]:
    """
    Create a database view from a SELECT query.
    
    Args:
        view_name: Name of the view to create
        select_query: SELECT query that defines the view
        replace_if_exists: If True, replaces existing view with same name
        
    Returns:
        Result with status and operation details
    """
    return create_view(view_name, select_query, replace_if_exists)


@mcp.tool()
def crud_create_index(index_name: str, table_name: str, columns: List[str], unique: bool = False) -> Dict[str, Any]:
    """
    Create a single or composite index on table columns.
    
    Args:
        index_name: Name of the index to create
        table_name: Name of the table
        columns: List of column names to include in index (e.g., ["email"] or ["last_name", "first_name"])
        unique: If True, creates a UNIQUE index
        
    Returns:
        Result with status and operation details
    """
    return create_index(index_name, table_name, columns, unique)


# ============================================
# CATEGORY 3: CRUD READ OPERATIONS (2 tools)
# ============================================

@mcp.tool()
def crud_query(
    query: str, 
    params: Optional[List[Any]] = None, 
    limit: Optional[int] = None, 
    offset: Optional[int] = None
) -> Dict[str, Any]:
    """
    Execute a raw SELECT query with optional parameters and pagination.
    
    Use this for complex queries with JOINs, aggregations, or custom logic.
    For simple table queries, use crud_get() instead.
    
    Args:
        query: SELECT query to execute (use %s for parameterized values)
        params: Optional list of parameter values to substitute in query
        limit: Optional maximum number of records to return
        offset: Optional number of records to skip (for pagination)
        
    Example:
        query = "SELECT * FROM users WHERE age > %s AND city = %s"
        params = [30, "NYC"]
        
    Returns:
        Result with query results, column names, and row count
    """
    return query_data(query, params, limit, offset)


@mcp.tool()
def crud_get(
    table_name: str,
    mode: str = "records",
    where_clause: Optional[str] = None,
    where_params: Optional[List[Any]] = None,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    High-level data retrieval from a table (unified read operations).
    
    Args:
        table_name: Name of the table to query
        mode: Type of operation:
            - "records": Get filtered records (default)
            - "count": Count records matching filter
            - "distinct": Get distinct values for a column
            - "paginate": Get paginated results with metadata
        where_clause: Optional SQL WHERE clause (use %s for parameters)
        where_params: Optional list of values for WHERE clause parameters
        options: Optional dict with mode-specific options:
            For "records": {limit, offset, order_by, column_name}
            For "count": (no additional options)
            For "distinct": {column_name, limit}
            For "paginate": {page, page_size, order_by}
            
    Examples:
        - Get records: mode="records", where_clause="age > %s", where_params=[30], 
                       options={"limit": 10, "order_by": "name ASC"}
        - Count: mode="count", where_clause="status = %s", where_params=["active"]
        - Distinct: mode="distinct", options={"column_name": "city", "limit": 50}
        - Paginate: mode="paginate", options={"page": 2, "page_size": 20}
    
    Returns:
        Result with data based on selected mode
    """
    try:
        options = options or {}
        
        if mode == "records":
            return get_records(
                table_name,
                where_clause=where_clause,
                where_params=where_params,
                limit=options.get("limit"),
                offset=options.get("offset"),
                order_by=options.get("order_by")
            )
            
        elif mode == "count":
            return get_record_count(
                table_name,
                where_clause=where_clause,
                where_params=where_params
            )
            
        elif mode == "distinct":
            column_name = options.get("column_name")
            if not column_name:
                return {
                    "status": "error",
                    "error": "mode='distinct' requires options={'column_name': 'col'}"
                }
            return distinct_values(
                table_name,
                column_name,
                limit=options.get("limit")
            )
            
        elif mode == "paginate":
            return paginate_data(
                table_name,
                page=options.get("page", 1),
                page_size=options.get("page_size", 10),
                order_by=options.get("order_by"),
                where_clause=where_clause,
                where_params=where_params
            )
            
        else:
            return {
                "status": "error",
                "error": f"Unknown mode: '{mode}'. Valid options: 'records', 'count', 'distinct', 'paginate'"
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


# ============================================
# CATEGORY 4: CRUD UPDATE OPERATIONS (2 tools)
# ============================================

@mcp.tool()
def crud_update(
    table_name: str,
    values: Dict[str, Any],
    where_clause: Optional[str] = None,
    where_params: Optional[List[Any]] = None,
    id_column: Optional[str] = None,
    record_id: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Update records in a table (supports single, batch, and column updates).
    
    Three update modes:
    1. Single record by ID: Provide record_id and id_column
    2. Batch update: Provide where_clause and where_params
    3. Column-only update: Use special key "_column_only" in values
    
    Args:
        table_name: Name of the table to update
        values: Dictionary of column-value pairs to update
        where_clause: Optional WHERE clause for batch updates (use %s for parameters)
        where_params: Optional list of values for WHERE clause parameters
        id_column: Column name for ID-based updates (e.g., "id", "user_id")
        record_id: ID value for single record update
        
    Examples:
        - Single record: record_id=123, id_column="id", values={"name": "John", "age": 30}
        - Batch update: where_clause="age > %s", where_params=[30], values={"status": "active"}
        - Column update: values={"status": "active"}, where_clause="city = %s", where_params=["NYC"]
        
    Returns:
        Result with status, updated count, and operation details
    """
    try:
        # Single record update by ID
        if record_id is not None and id_column:
            return update_record(table_name, record_id, id_column, values)
        
        # Batch or column update
        elif where_clause and where_params:
            # Check if it's a single-column bulk update
            if len(values) == 1 and "_column_only" not in values:
                column_name = list(values.keys())[0]
                new_value = values[column_name]
                return update_column(table_name, column_name, new_value, where_clause, where_params)
            else:
                return update_records_batch(table_name, where_clause, where_params, values)
        
        else:
            return {
                "status": "error",
                "error": "Must provide either (record_id + id_column) or (where_clause + where_params)"
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@mcp.tool()
def crud_rename(
    object_type: str,
    old_name: str,
    new_name: str,
    table_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Rename database objects (tables or columns).
    
    Args:
        object_type: Type of object to rename:
            - "table": Rename a table
            - "column": Rename a column (requires table_name)
        old_name: Current name of the object
        new_name: New name for the object
        table_name: Required when object_type="column", specifies which table contains the column
        
    Examples:
        - Rename table: object_type="table", old_name="users_old", new_name="users"
        - Rename column: object_type="column", table_name="users", old_name="usr_name", new_name="username"
        
    Returns:
        Result with status and operation details
    """
    try:
        if object_type == "table":
            return rename_table(old_name, new_name)
            
        elif object_type == "column":
            if not table_name:
                return {
                    "status": "error",
                    "error": "table_name is required when renaming a column"
                }
            return rename_column(table_name, old_name, new_name)
            
        else:
            return {
                "status": "error",
                "error": f"Unknown object_type: '{object_type}'. Valid options: 'table', 'column'"
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


# ============================================
# CATEGORY 5: CRUD DELETE OPERATIONS (1 tool)
# ============================================

@mcp.tool()
def crud_delete(
    table_name: str,
    mode: str = "records",
    where_clause: Optional[str] = None,
    where_params: Optional[List[Any]] = None,
    id_column: Optional[str] = None,
    record_id: Optional[Any] = None,
    cascade: bool = False
) -> Dict[str, Any]:
    """
    Delete data or drop tables (unified deletion operations).
    
    Args:
        table_name: Name of the table
        mode: Deletion scope:
            - "records": Delete specific records matching WHERE clause (supports single or batch)
            - "truncate": Remove all data from table (fast, resets sequences)
            - "drop": Drop the entire table (WARNING: destroys table structure and data)
        where_clause: WHERE clause for "records" mode (use %s for parameters)
        where_params: List of values for WHERE clause parameters
        id_column: Column name for single record deletion by ID (e.g., "id")
        record_id: ID value for single record deletion
        cascade: For "drop" mode, also drop dependent objects (views, foreign keys, etc.)
        
    Examples:
        - Delete single: mode="records", record_id=123, id_column="id"
        - Delete batch: mode="records", where_clause="age > %s", where_params=[30]
        - Truncate: mode="truncate"
        - Drop table: mode="drop", cascade=True
        
    Returns:
        Result with status and operation details
    """
    try:
        if mode == "records":
            # Single record deletion by ID
            if record_id is not None and id_column:
                return delete_record(table_name, record_id, id_column)
            # Batch deletion with WHERE clause
            elif where_clause and where_params:
                return delete_records(table_name, where_clause, where_params)
            else:
                return {
                    "status": "error",
                    "error": "mode='records' requires either (record_id + id_column) or (where_clause + where_params)"
                }
                
        elif mode == "truncate":
            return truncate_table(table_name)
            
        elif mode == "drop":
            return drop_table(table_name, cascade)
            
        else:
            return {
                "status": "error",
                "error": f"Unknown mode: '{mode}'. Valid options: 'records', 'truncate', 'drop'"
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }



# ============================================
# CATEGORY 6: SCHEMA MODIFICATION (5 tools)
# ============================================

@mcp.tool()
def mod_column(
    table_name: str,
    action: str,
    column_name: str,
    column_spec: Optional[Dict[str, Any]] = None,
    cascade: bool = False
) -> Dict[str, Any]:
    """
    Unified column management (add, modify type, drop, set nullable).
    
    Args:
        table_name: Name of the table
        action: Column operation:
            - "add": Add a new column to the table
            - "modify_type": Change the data type of an existing column
            - "drop": Remove a column from the table
            - "set_nullable": Change NULL constraint on a column
        column_name: Name of the column (for add, use column_spec["name"] instead)
        column_spec: Dict with action-specific parameters:
            For "add": {"name": "col_name", "type": "VARCHAR(255)", "nullable": True}
            For "modify_type": {"new_type": "TEXT", "using_expression": "column::text"}
            For "set_nullable": {"is_nullable": True}
        cascade: For "drop" action, also drop dependent objects
        
    Examples:
        - Add: action="add", column_spec={"name": "status", "type": "VARCHAR(50)", "nullable": False}
        - Modify: action="modify_type", column_name="age", column_spec={"new_type": "BIGINT"}
        - Drop: action="drop", column_name="old_field", cascade=True
        - Nullable: action="set_nullable", column_name="email", column_spec={"is_nullable": True}
        
    Returns:
        Result with status and operation details
    """
    try:
        column_spec = column_spec or {}
        
        if action == "add":
            if not column_spec or "name" not in column_spec or "type" not in column_spec:
                return {
                    "status": "error",
                    "error": "action='add' requires column_spec with 'name' and 'type'"
                }
            return schema_add_column(table_name, column_spec)
            
        elif action == "modify_type":
            new_type = column_spec.get("new_type")
            if not new_type:
                return {
                    "status": "error",
                    "error": "action='modify_type' requires column_spec={'new_type': '...'}"
                }
            return schema_modify_column_type(
                table_name,
                column_name,
                new_type,
                using_expression=column_spec.get("using_expression")
            )
            
        elif action == "drop":
            return schema_drop_column(table_name, column_name, cascade)
            
        elif action == "set_nullable":
            is_nullable = column_spec.get("is_nullable")
            if is_nullable is None:
                return {
                    "status": "error",
                    "error": "action='set_nullable' requires column_spec={'is_nullable': True/False}"
                }
            return schema_set_column_nullable(table_name, column_name, is_nullable)
            
        else:
            return {
                "status": "error",
                "error": f"Unknown action: '{action}'. Valid options: 'add', 'modify_type', 'drop', 'set_nullable'"
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@mcp.tool()
def mod_index(
    action: str,
    index_name: Optional[str] = None,
    table_name: Optional[str] = None,
    cascade: bool = False
) -> Dict[str, Any]:
    """
    Manage database indexes (list and drop operations).
    
    Note: For creating indexes, use crud_create_index().
    
    Args:
        action: Index operation:
            - "list": List all indexes (optionally filtered by table)
            - "drop": Drop/remove an index
        index_name: Required for "drop" action
        table_name: Optional filter for "list" action
        cascade: For "drop" action, also drop dependent objects
        
    Examples:
        - List all: action="list"
        - List for table: action="list", table_name="users"
        - Drop: action="drop", index_name="idx_users_email", cascade=False
        
    Returns:
        Result with index information or operation status
    """
    try:
        if action == "list":
            return schema_list_indexes(table_name)
            
        elif action == "drop":
            if not index_name:
                return {
                    "status": "error",
                    "error": "action='drop' requires index_name"
                }
            return schema_drop_index(index_name, cascade)
            
        else:
            return {
                "status": "error",
                "error": f"Unknown action: '{action}'. Valid options: 'list', 'drop'"
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@mcp.tool()
def mod_constraint(
    action: str,
    table_name: Optional[str] = None,
    constraint_name: Optional[str] = None,
    cascade: bool = False
) -> Dict[str, Any]:
    """
    Manage database constraints (list and drop operations).
    
    Note: For adding constraints, use mod_add_constraint().
    
    Args:
        action: Constraint operation:
            - "list": List all constraints (optionally filtered by table)
            - "drop": Drop/remove a constraint
        table_name: Required for "drop", optional filter for "list"
        constraint_name: Required for "drop" action
        cascade: For "drop" action, also drop dependent objects
        
    Examples:
        - List all: action="list"
        - List for table: action="list", table_name="users"
        - Drop: action="drop", table_name="users", constraint_name="fk_users_dept", cascade=True
        
    Returns:
        Result with constraint information or operation status
    """
    try:
        if action == "list":
            return schema_list_constraints(table_name)
            
        elif action == "drop":
            if not table_name or not constraint_name:
                return {
                    "status": "error",
                    "error": "action='drop' requires both table_name and constraint_name"
                }
            return schema_drop_constraint(table_name, constraint_name, cascade)
            
        else:
            return {
                "status": "error",
                "error": f"Unknown action: '{action}'. Valid options: 'list', 'drop'"
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@mcp.tool()
def mod_add_constraint(
    constraint_type: str,
    table_name: str,
    spec: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Add constraints to a table (primary key or foreign key).
    
    Args:
        constraint_type: Type of constraint:
            - "primary_key": Add a primary key constraint
            - "foreign_key": Add a foreign key constraint
        table_name: Name of the table to add the constraint to
        spec: Constraint specification dict:
            For "primary_key": {
                "columns": ["id"],  # or ["col1", "col2"] for composite
                "constraint_name": "pk_users"  # optional
            }
            For "foreign_key": {
                "columns": ["user_id"],
                "ref_table": "users",
                "ref_columns": ["id"],
                "constraint_name": "fk_orders_user",  # optional
                "on_delete": "CASCADE"  # optional: CASCADE, RESTRICT, SET NULL, SET DEFAULT, NO ACTION
            }
            
    Examples:
        - Primary key: constraint_type="primary_key", table_name="users", 
                       spec={"columns": ["id"]}
        - Foreign key: constraint_type="foreign_key", table_name="orders",
                       spec={"columns": ["user_id"], "ref_table": "users", "ref_columns": ["id"], "on_delete": "CASCADE"}
        
    Returns:
        Result with status and operation details
    """
    try:
        if constraint_type == "primary_key":
            columns = spec.get("columns")
            if not columns:
                return {
                    "status": "error",
                    "error": "constraint_type='primary_key' requires spec={'columns': [...]}"
                }
            return schema_add_primary_key(
                table_name,
                columns,
                constraint_name=spec.get("constraint_name")
            )
            
        elif constraint_type == "foreign_key":
            columns = spec.get("columns")
            ref_table = spec.get("ref_table")
            ref_columns = spec.get("ref_columns")
            
            if not all([columns, ref_table, ref_columns]):
                return {
                    "status": "error",
                    "error": "constraint_type='foreign_key' requires spec with 'columns', 'ref_table', 'ref_columns'"
                }
                
            return schema_add_foreign_key(
                table_name,
                columns,
                ref_table,
                ref_columns,
                constraint_name=spec.get("constraint_name"),
                on_delete=spec.get("on_delete", "NO ACTION")
            )
            
        else:
            return {
                "status": "error",
                "error": f"Unknown constraint_type: '{constraint_type}'. Valid options: 'primary_key', 'foreign_key'"
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@mcp.tool()
def mod_view(
    action: str,
    view_name: Optional[str] = None,
    cascade: bool = False
) -> Dict[str, Any]:
    """
    Manage database views (list, get definition, and drop operations).
    
    Note: For creating views, use crud_create_view().
    
    Args:
        action: View operation:
            - "list": List all user-defined views in the database
            - "get": Get the SQL definition of a specific view
            - "drop": Drop/remove a view
        view_name: Required for "get" and "drop" actions
        cascade: For "drop" action, also drop dependent objects
        
    Examples:
        - List all: action="list"
        - Get definition: action="get", view_name="active_users_view"
        - Drop: action="drop", view_name="old_view", cascade=True
        
    Returns:
        Result with view information or operation status
    """
    try:
        if action == "list":
            return schema_list_views()
            
        elif action == "get":
            if not view_name:
                return {
                    "status": "error",
                    "error": "action='get' requires view_name"
                }
            return schema_get_view_definition(view_name)
            
        elif action == "drop":
            if not view_name:
                return {
                    "status": "error",
                    "error": "action='drop' requires view_name"
                }
            return schema_drop_view(view_name, cascade)
            
        else:
            return {
                "status": "error",
                "error": f"Unknown action: '{action}'. Valid options: 'list', 'get', 'drop'"
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


if __name__ == "__main__":
    mcp.run()
