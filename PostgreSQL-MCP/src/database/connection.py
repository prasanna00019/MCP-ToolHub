"""
Database connection management module.
Handles PostgreSQL connection creation and cleanup.
"""

import psycopg2
from psycopg2.extensions import connection as psycopg2_connection
from src.config import DatabaseConfig


def get_connection() -> psycopg2_connection:
    """
    Create and return a PostgreSQL database connection.
    
    Returns:
        psycopg2.extensions.connection: Active database connection
        
    Raises:
        psycopg2.Error: If connection fails
    """
    try:
        conn = psycopg2.connect(**DatabaseConfig.to_dict())
        return conn
    except psycopg2.Error as e:
        raise Exception(f"Failed to connect to database: {e}")
