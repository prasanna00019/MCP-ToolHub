"""
Validation module for CRUD operations.
Ensures input safety and data integrity before database operations.
"""

from typing import Any, Dict, List, Optional
import re


class CRUDValidator:
    """Validates inputs for CRUD operations."""

    @staticmethod
    def validate_table_name(table_name: str) -> bool:
        """
        Validate table name format (alphanumeric + underscore).
        
        Args:
            table_name: Table name to validate
            
        Returns:
            bool: True if valid
            
        Raises:
            ValueError: If invalid format
        """
        if not table_name or not isinstance(table_name, str):
            raise ValueError("Table name must be a non-empty string")
        
        # PostgreSQL identifier rules: start with letter/underscore, then alphanumeric/underscore
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", table_name):
            raise ValueError(
                f"Invalid table name '{table_name}'. Must start with letter or underscore, "
                "contain only alphanumeric characters and underscores."
            )
        
        # Check for PostgreSQL reserved keywords (common ones)
        reserved = {
            "select", "from", "where", "insert", "update", "delete", "create", 
            "drop", "alter", "table", "view", "index", "schema", "database"
        }
        if table_name.lower() in reserved:
            raise ValueError(f"'{table_name}' is a PostgreSQL reserved keyword")
        
        return True

    @staticmethod
    def validate_column_name(column_name: str) -> bool:
        """Validate column name format."""
        if not column_name or not isinstance(column_name, str):
            raise ValueError("Column name must be a non-empty string")
        
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", column_name):
            raise ValueError(
                f"Invalid column name '{column_name}'. Must start with letter or underscore, "
                "contain only alphanumeric characters and underscores."
            )
        
        return True

    @staticmethod
    def validate_column_type(data_type: str) -> bool:
        """
        Validate PostgreSQL data type.
        
        Args:
            data_type: SQL data type (e.g., 'INTEGER', 'VARCHAR(255)', 'DECIMAL(10,2)')
            
        Returns:
            bool: True if valid
        """
        if not data_type or not isinstance(data_type, str):
            raise ValueError("Data type must be a non-empty string")
        
        # Extract base type
        base_type = data_type.split('(')[0].upper().strip()
        
        valid_types = {
            # Numeric
            "SMALLINT", "INTEGER", "BIGINT", "DECIMAL", "NUMERIC", "REAL", "DOUBLE PRECISION",
            "SERIAL", "BIGSERIAL",
            # String
            "CHARACTER", "CHAR", "VARCHAR", "TEXT",
            # Date/Time
            "DATE", "TIME", "TIMESTAMP", "INTERVAL",
            # Boolean
            "BOOLEAN",
            # Binary
            "BYTEA",
            # JSON
            "JSON", "JSONB",
            # UUID
            "UUID",
            # Arrays
            "ARRAY",
        }
        
        if base_type not in valid_types:
            raise ValueError(
                f"Unknown data type '{data_type}'. Valid types: {', '.join(sorted(valid_types))}"
            )
        
        return True

    @staticmethod
    def validate_where_clause(where_clause: Optional[str]) -> bool:
        """
        Basic validation of WHERE clause format.
        
        Args:
            where_clause: SQL WHERE clause (without WHERE keyword)
            
        Returns:
            bool: True if valid
        """
        if where_clause is None:
            return True
        
        if not isinstance(where_clause, str):
            raise ValueError("WHERE clause must be a string")
        
        # Check for common SQL injection patterns
        dangerous_patterns = [
            r";\s*DROP",
            r";\s*DELETE",
            r";\s*TRUNCATE",
            r";\s*CREATE",
            r"--\s*$",  # SQL comments at end
            r"/\*",     # Block comments
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, where_clause, re.IGNORECASE):
                raise ValueError(
                    "WHERE clause contains potentially dangerous SQL. "
                    "Only use simple filtering conditions."
                )
        
        return True

    @staticmethod
    def validate_values_dict(values: Dict[str, Any]) -> bool:
        """
        Validate record values dictionary.
        
        Args:
            values: Dictionary of column_name: value pairs
            
        Returns:
            bool: True if valid
        """
        if not isinstance(values, dict):
            raise ValueError("Values must be a dictionary")
        
        if not values:
            raise ValueError("Values dictionary must not be empty")
        
        # Validate each column name
        for col_name in values.keys():
            CRUDValidator.validate_column_name(col_name)
        
        return True

    @staticmethod
    def validate_values_list(records: List[Dict[str, Any]]) -> bool:
        """
        Validate list of record dictionaries.
        
        Args:
            records: List of dictionaries with column_name: value pairs
            
        Returns:
            bool: True if valid
        """
        if not isinstance(records, list):
            raise ValueError("Records must be a list")
        
        if not records:
            raise ValueError("Records list must not be empty")
        
        # All records must have same structure
        first_keys = set(records[0].keys())
        for i, record in enumerate(records[1:], 1):
            if set(record.keys()) != first_keys:
                raise ValueError(
                    f"Record {i} has different columns than first record. "
                    f"All records must have identical column structure."
                )
            CRUDValidator.validate_values_dict(record)
        
        return True

    @staticmethod
    def validate_order_by(order_by: Optional[str]) -> bool:
        """
        Validate ORDER BY clause.
        
        Args:
            order_by: ORDER BY clause (e.g., 'name ASC, age DESC')
            
        Returns:
            bool: True if valid
        """
        if order_by is None:
            return True
        
        if not isinstance(order_by, str):
            raise ValueError("ORDER BY clause must be a string")
        
        # Check for dangerous SQL
        if ";" in order_by or "--" in order_by or "/*" in order_by:
            raise ValueError("ORDER BY clause contains forbidden characters")
        
        return True

    @staticmethod
    def validate_limit_offset(limit: Optional[int], offset: Optional[int]) -> bool:
        """
        Validate LIMIT and OFFSET values.
        
        Args:
            limit: Limit value
            offset: Offset value
            
        Returns:
            bool: True if valid
        """
        if limit is not None:
            if not isinstance(limit, int) or limit < 0:
                raise ValueError("LIMIT must be a non-negative integer")
        
        if offset is not None:
            if not isinstance(offset, int) or offset < 0:
                raise ValueError("OFFSET must be a non-negative integer")
        
        return True

    @staticmethod
    def validate_primary_key(pk_columns: List[str]) -> bool:
        """
        Validate primary key column list.
        
        Args:
            pk_columns: List of column names for primary key
            
        Returns:
            bool: True if valid
        """
        if not isinstance(pk_columns, list) or not pk_columns:
            raise ValueError("Primary key must be a non-empty list of column names")
        
        for col in pk_columns:
            CRUDValidator.validate_column_name(col)
        
        return True

    @staticmethod
    def validate_foreign_key(
        column: str,
        ref_table: str,
        ref_column: str,
        on_delete: str = "RESTRICT",
        on_update: str = "RESTRICT"
    ) -> bool:
        """
        Validate foreign key definition.
        
        Args:
            column: Local column name
            ref_table: Referenced table name
            ref_column: Referenced column name
            on_delete: ON DELETE action (RESTRICT, CASCADE, SET NULL, SET DEFAULT)
            on_update: ON UPDATE action (same options)
            
        Returns:
            bool: True if valid
        """
        CRUDValidator.validate_column_name(column)
        CRUDValidator.validate_table_name(ref_table)
        CRUDValidator.validate_column_name(ref_column)
        
        valid_actions = {"RESTRICT", "CASCADE", "SET NULL", "SET DEFAULT", "NO ACTION"}
        if on_delete.upper() not in valid_actions:
            raise ValueError(f"Invalid ON DELETE action: {on_delete}")
        if on_update.upper() not in valid_actions:
            raise ValueError(f"Invalid ON UPDATE action: {on_update}")
        
        return True
