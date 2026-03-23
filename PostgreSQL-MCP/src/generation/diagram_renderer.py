"""
Diagram rendering module.
Renders PlantUML diagrams to image files (PNG, SVG, PDF).
Uses PlantUML's HTTP API.
"""

import requests
import zlib
import base64
import string
from pathlib import Path
from typing import Dict, Optional, Literal


def encode_plantuml(text: str) -> str:
    """Encode PlantUML syntax to its custom base64 format."""
    zlibbed_str = zlib.compress(text.encode('utf-8'))
    compressed_string = zlibbed_str[2:-4]
    return base64.b64encode(compressed_string).decode('utf-8').translate(
        str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/',
                      '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_')
    )

class DiagramRenderer:
    """
    Renders PlantUML diagrams via standard PlantUML webservice.
    """
    
    PLANTUML_API_BASE = "http://www.plantuml.com/plantuml"
    
    def __init__(self, output_dir: str = "diagrams"):
        """
        Initialize diagram renderer.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def render_to_file(
        self,
        plantuml_syntax: str,
        filename: str,
        format: Literal["png", "svg", "pdf"] = "svg"
    ) -> Optional[Path]:
        """
        Render PlantUML diagram to file.
        
        Args:
            plantuml_syntax: PlantUML diagram syntax
            filename: Output filename (without extension)
            format: Output format (png, svg, pdf)
            
        Returns:
            Path to rendered file, or None if rendering failed
        """
        return self._render_api(plantuml_syntax, filename, format)
    
    def _render_api(
        self,
        plantuml_syntax: str,
        filename: str,
        format: str
    ) -> Optional[Path]:
        """Render using plantuml.com API."""
        try:
            encoded = encode_plantuml(plantuml_syntax)
            
            format_map = {
                "png": "png",
                "svg": "svg",
                "pdf": "pdf"
            }
            
            api_format = format_map.get(format, "svg")
            url = f"{self.PLANTUML_API_BASE}/{api_format}/{encoded}"
            
            # Make API request
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Save to file
            output_file = self.output_dir / f"{filename}.{format}"
            output_file.write_bytes(response.content)
            
            return output_file
            
        except requests.RequestException as e:
            print(f"API rendering failed ({e.__class__.__name__}): {e}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None
    
    def render_erd(self, schema: Dict, output_format: str = "svg", filename: str = "database_erd") -> Optional[Path]:
        from .plantuml_gen import generate_plantuml_erd
        syntax = generate_plantuml_erd(schema)
        return self.render_to_file(syntax, filename, output_format)
    
    def render_class_diagram(self, schema: Dict, output_format: str = "svg", filename: str = "database_class") -> Optional[Path]:
        from .plantuml_gen import generate_plantuml_class
        syntax = generate_plantuml_class(schema)
        return self.render_to_file(syntax, filename, output_format)
        
    def render_component_diagram(self, schema: Dict, output_format: str = "svg", filename: str = "database_component") -> Optional[Path]:
        from .plantuml_gen import generate_plantuml_component
        syntax = generate_plantuml_component(schema)
        return self.render_to_file(syntax, filename, output_format)
    
    def get_diagram_path(self, filename: str) -> Path:
        """Get full path for a diagram file."""
        return self.output_dir / filename


def render_database_diagrams(
    schema: Dict,
    output_dir: str = "diagrams",
    formats: list = ["svg", "png"]
) -> Dict[str, Path]:
    """
    Render all database diagrams via PlantUML.
    """
    renderer = DiagramRenderer(output_dir)
    results = {}
    
    for format in formats:
        # Render ERD
        erd_path = renderer.render_erd(schema, format, f"erd_{format}")
        if erd_path:
            results[f"erd_{format}"] = erd_path
            
        class_path = renderer.render_class_diagram(schema, format, f"class_{format}")
        if class_path:
            results[f"class_{format}"] = class_path
            
        comp_path = renderer.render_component_diagram(schema, format, f"component_{format}")
        if comp_path:
            results[f"component_{format}"] = comp_path
    
    return results
