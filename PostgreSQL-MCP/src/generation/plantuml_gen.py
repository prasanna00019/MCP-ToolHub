"""
PlantUML diagram generation module.
Generates various diagrams (ERD, Class, Component) in PlantUML syntax.
"""

from typing import Dict


def generate_plantuml_erd(schema: Dict) -> str:
    """
    Generate a PlantUML Entity-Relationship Diagram from schema.
    
    Args:
        schema: Database schema dictionary
        
    Returns:
        str: PlantUML ERD syntax
    """
    lines = ["@startuml", "hide circle", "skinparam linetype ortho"]

    # Add entities with columns
    for table, info in schema.items():
        lines.append(f"entity \"{table}\" as {table} {{")
        # primary keys first if identifiable
        for col in info["columns"]:
            col_name = col['name']
            col_type = col['type']
            marks = ""
            if any(col_name in pk for pk in info.get("primary_keys", [])):
                marks = "  * "
            else:
                marks = "  "
            lines.append(f"{marks}{col_name} : {col_type}")
        lines.append("}")

    # Add relationships
    for table, info in schema.items():
        for fk in info["foreign_keys"]:
            ref_table = fk['references_table']
            nullable = fk.get("nullable", True)
            relationship = "}o--||" if nullable else "}o-||"
            lines.append(f"{table} {relationship} {ref_table} : \"{fk['column']}\"")

    lines.append("@enduml")
    return "\n".join(lines)


def generate_plantuml_class(schema: Dict) -> str:
    """
    Generate a PlantUML Class Diagram from schema.
    
    Args:
        schema: Database schema dictionary
        
    Returns:
        str: PlantUML Class diagram syntax
    """
    lines = ["@startuml"]
    
    for table, info in schema.items():
        lines.append(f"class {table} {{")
        for col in info["columns"]:
            lines.append(f"  + {col['name']}: {col['type']}")
        lines.append("}")
        
    for table, info in schema.items():
        for fk in info["foreign_keys"]:
            lines.append(f"{table} --> {fk['references_table']} : {fk['column']}")
            
    lines.append("@enduml")
    return "\n".join(lines)


def generate_plantuml_component(schema: Dict) -> str:
    """
    Generate a PlantUML Component Diagram showing architecture from schema.
    
    Args:
        schema: Database schema dictionary
        
    Returns:
        str: PlantUML Component diagram syntax
    """
    lines = ["@startuml"]
    
    for table in schema.keys():
        lines.append(f"component [{table}]")
        
    for table, info in schema.items():
        for fk in info["foreign_keys"]:
            lines.append(f"[{table}] ..> [{fk['references_table']}] : uses")
            
    lines.append("@enduml")
    return "\n".join(lines)
