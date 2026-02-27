"""
SchemaIntelligence MCP Server
AI-powered PostgreSQL database analysis and documentation
"""

from mcp.server.fastmcp import FastMCP
from typing import Dict
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

# Initialize MCP Server
mcp = FastMCP("SchemaIntelligence")


# ============================================
# MCP TOOLS
# ============================================

@mcp.tool()
def analyze_database() -> Dict:
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
def explain_database() -> Dict:
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
def list_tables() -> Dict:
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
def check_ollama_status() -> Dict:
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
def render_database_diagrams(output_format: str = "svg") -> Dict:
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


if __name__ == "__main__":
    mcp.run()
