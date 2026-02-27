"""
Ollama LLM integration module.
Handles communication with Ollama for AI-powered schema analysis.
"""

import json
import requests
from typing import Dict, Optional
from src.config import OllamaConfig


class OllamaAnalyzer:
    """
    Interface to Ollama LLM for analyzing database schemas.
    Generates AI-powered explanations and recommendations.
    """
    
    def __init__(self, model: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize Ollama analyzer.
        
        Args:
            model: Model name (defaults to config)
            base_url: Ollama API base URL (defaults to config)
        """
        self.model = model or OllamaConfig.MODEL
        self.base_url = base_url or OllamaConfig.BASE_URL
        self.timeout = OllamaConfig.TIMEOUT
    
    def explain_schema(self, schema: Dict) -> Dict:
        """
        Use Ollama to generate AI-powered explanation of database schema.
        
        Args:
            schema: Database schema dictionary
            
        Returns:
            Dict: Analysis including business explanation, relationships,
                  join recommendations, ERD, and quality insights
        """
        
        prompt = f"""You are a senior database architect.

Analyze the following PostgreSQL schema JSON.

Tasks:
1. Explain what this database likely does in business terms.
2. Identify relationships (explicit or implicit).
3. Detect possible foreign keys based on column naming like *_id.
4. Suggest join types (INNER vs LEFT).
5. Generate an improved Mermaid ER diagram.
6. Provide insights about structure quality.

Return response in structured JSON with keys:
- business_explanation (string)
- detected_relationships (list of dicts)
- join_recommendations (list of dicts)
- mermaid_erd (string)
- insights (list of strings)

Schema:
{json.dumps(schema, indent=2)}
"""

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()["response"]
            
            # Try to parse as JSON, fall back to string if not valid JSON
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return {"llm_analysis": result}
                
        except requests.RequestException as e:
            return {"error": f"Failed to call Ollama: {str(e)}"}
    
    def get_available_models(self) -> list:
        """
        Fetch available models from Ollama server.
        
        Returns:
            list: List of available model names
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except requests.RequestException as e:
            return []
    
    def is_available(self) -> bool:
        """
        Check if Ollama server is available and model exists.
        
        Returns:
            bool: True if server is reachable and model exists
        """
        try:
            models = self.get_available_models()
            return self.model in models
        except:
            return False
