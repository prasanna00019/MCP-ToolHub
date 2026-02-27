"""
Configuration module for SchemaIntelligence.
Handles database and Ollama/LLM configuration.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class DatabaseConfig:
    """Database connection configuration"""
    HOST = os.getenv("DB_HOST", "localhost")
    PORT = os.getenv("DB_PORT", "6739")
    DATABASE = os.getenv("DB_NAME")
    USER = os.getenv("DB_USER", "postgres")
    PASSWORD = os.getenv("DB_PASSWORD", )

    @classmethod
    def to_dict(cls):
        """Convert config to connection dictionary"""
        return {
            "host": cls.HOST,
            "port": int(cls.PORT) if isinstance(cls.PORT, str) else cls.PORT,
            "database": cls.DATABASE,
            "user": cls.USER,
            "password": cls.PASSWORD,
        }


class OllamaConfig:
    """Ollama/LLM configuration"""
    BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://192.168.1.143:11434")
    MODEL = os.getenv("OLLAMA_MODEL", "deepseek-r1:14b")
    TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "30"))


class AppConfig:
    """Application-level configuration"""
    LOG_FILE = "mcp_client_debug.log"
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
