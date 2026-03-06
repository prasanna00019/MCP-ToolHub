"""
Validation module for Schema Modification operations (Phase 2).
"""

from typing import Any, Dict, List, Optional
import re
from src.crud.crud_validator import CRUDValidator


class SchemaModValidator(CRUDValidator):
    """Extends CRUDValidator for DDL specific operations."""
    
    @staticmethod
    def validate_constraint_name(constraint_name: Optional[str]) -> bool:
        if constraint_name is None:
            return True
            
        if not isinstance(constraint_name, str):
            raise ValueError("Constraint name must be a string")
            
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", constraint_name):
            raise ValueError(
                f"Invalid constraint name '{constraint_name}'. Must start with letter or underscore, "
                "contain only alphanumeric characters and underscores."
            )
        return True
        
    @staticmethod
    def validate_index_name(index_name: str) -> bool:
        if not index_name or not isinstance(index_name, str):
            raise ValueError("Index name must be a non-empty string")
            
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", index_name):
            raise ValueError(f"Invalid index name '{index_name}'")
        return True

    @staticmethod
    def validate_view_name(view_name: str) -> bool:
        return SchemaModValidator.validate_table_name(view_name)
