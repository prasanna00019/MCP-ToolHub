"""
Analysis and detection module.
Detects junction tables and suggests join operations.
"""

from typing import Dict, List


def detect_junction_tables(schema: Dict) -> List[str]:
    """
    Detect many-to-many junction/association tables.
    Tables with exactly 2 foreign keys and <= 4 columns are likely junctions.
    
    Args:
        schema: Database schema dictionary
        
    Returns:
        List[str]: Names of detected junction tables
    """
    junctions = []

    for table, info in schema.items():
        # Check if table has exactly 2 FK and few columns
        if len(info["foreign_keys"]) == 2 and len(info["columns"]) <= 4:
            junctions.append(table)

    return junctions


def suggest_joins(schema: Dict) -> List[Dict]:
    """
    Suggest appropriate SQL joins based on foreign key relationships.
    Uses nullability to determine between INNER and LEFT JOINs.
    
    Args:
        schema: Database schema dictionary
        
    Returns:
        List[Dict]: Join suggestions with:
            - left_table: Source table
            - right_table: Target table
            - join_condition: SQL join condition
            - join_type: INNER JOIN or LEFT JOIN
    """
    joins = []

    for table, info in schema.items():
        for fk in info["foreign_keys"]:
            # Use nullability to determine join type
            # If FK column is nullable, use LEFT JOIN, else INNER JOIN
            join_type = "LEFT JOIN" if fk["nullable"] else "INNER JOIN"

            joins.append({
                "left_table": table,
                "right_table": fk["references_table"],
                "join_condition": (
                    f"{table}.{fk['column']} = "
                    f"{fk['references_table']}.{fk['references_column']}"
                ),
                "join_type": join_type
            })

    return joins


def detect_implicit_relationships(schema: Dict) -> List[Dict]:
    """
    Detect implicit relationships based on column naming patterns.
    Looks for *_id columns that might be foreign keys not explicitly defined.
    
    Args:
        schema: Database schema dictionary
        
    Returns:
        List[Dict]: Potential implicit relationships
    """
    implicit_rels = []

    for table, info in schema.items():
        for col in info["columns"]:
            # Check if column name ends with _id and matches a table name
            col_name = col["name"]
            if col_name.endswith("_id") and col_name != "id":
                # Extract potential table name
                potential_table = col_name[:-3]  # Remove _id suffix
                
                # Check if this table exists
                if potential_table in schema:
                    # Check if it's not already an explicit FK
                    is_explicit = any(
                        fk["column"] == col_name 
                        for fk in info["foreign_keys"]
                    )
                    
                    if not is_explicit:
                        implicit_rels.append({
                            "table": table,
                            "column": col_name,
                            "potential_references": potential_table,
                            "potential_reference_column": "id"
                        })

    return implicit_rels
