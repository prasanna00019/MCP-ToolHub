"""
Mermaid diagram generation module.
Generates Entity-Relationship Diagrams in Mermaid syntax.
"""

from typing import Dict


def generate_mermaid_erd(schema: Dict) -> str:
    """
    Generate a Mermaid Entity-Relationship Diagram from schema.
    
    Args:
        schema: Database schema dictionary
        
    Returns:
        str: Mermaid ERD syntax
    """
    # Map PostgreSQL types to simpler names for Mermaid
    type_map = {
        'integer': 'int',
        'bigint': 'long',
        'smallint': 'short',
        'numeric': 'decimal',
        'decimal': 'decimal',
        'real': 'float',
        'double precision': 'double',
        'character varying': 'string',
        'varchar': 'string',
        'char': 'char',
        'text': 'text',
        'boolean': 'bool',
        'date': 'date',
        'time': 'time',
        'timestamp': 'datetime',
        'timestamp without time zone': 'datetime',
        'json': 'json',
        'jsonb': 'json',
        'uuid': 'uuid'
    }
    
    lines = ["erDiagram"]

    # Add entities with columns
    for table, info in schema.items():
        lines.append(f"  {table} {{")
        for col in info["columns"]:
            col_type = col['type'].lower()
            # Use type mapping, or original if not found
            mapped_type = type_map.get(col_type, col_type.replace(' ', '_'))
            col_name = col['name']
            lines.append(f"    {mapped_type} {col_name}")
        lines.append("  }")

    # Add relationships from foreign keys
    for table, info in schema.items():
        for fk in info["foreign_keys"]:
            relationship_type = "||--o|" if fk["nullable"] else "||--|"
            lines.append(
                f"  {table} {relationship_type} {fk['references_table']} : \"{fk['column']}\""
            )

    return "\n".join(lines)


def generate_mermaid_flowchart(schema: Dict) -> str:
    """
    Generate a Mermaid flowchart showing table relationships and data flow.
    
    Args:
        schema: Database schema dictionary
        
    Returns:
        str: Mermaid flowchart syntax
    """
    lines = ["graph LR"]
    
    for table, info in schema.items():
        lines.append(f"  {table}[<b>{table}</b>]")
        
        for fk in info["foreign_keys"]:
            # Create directed relationship
            relationship_label = fk['column']
            lines.append(f"  {table} -->|{relationship_label}| {fk['references_table']}")
    
    return "\n".join(lines)
