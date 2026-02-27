"""
Diagram rendering module.
Renders Mermaid diagrams to image files (PNG, SVG, PDF).
Supports both API-based and CLI-based rendering.
"""

import subprocess
import base64
import requests
from pathlib import Path
from typing import Dict, Optional, Literal


class DiagramRenderer:
    """
    Renders Mermaid diagrams to multiple output formats.
    Tries subprocess (mermaid-cli) first, falls back to API.
    """
    
    # Mermaid.ink API endpoint for rendering
    MERMAID_API_BASE = "https://mermaid.ink"
    
    def __init__(self, output_dir: str = "diagrams"):
        """
        Initialize diagram renderer.
        
        Args:
            output_dir: Directory to save rendered diagrams
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self._cli_available = self._check_mermaid_cli()
    
    def _check_mermaid_cli(self) -> bool:
        """Check if mermaid-cli is available (mmdc or npx)."""
        try:
            # Try mmdc first
            result = subprocess.run(
                ["mmdc", "--version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        try:
            # Try npx as fallback
            result = subprocess.run(
                ["npx", "@mermaid-js/mermaid-cli", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def render_to_file(
        self,
        mermaid_syntax: str,
        filename: str,
        format: Literal["png", "svg", "pdf"] = "svg"
    ) -> Optional[Path]:
        """
        Render Mermaid diagram to file.
        
        Args:
            mermaid_syntax: Mermaid diagram syntax
            filename: Output filename (without extension)
            format: Output format (png, svg, pdf)
            
        Returns:
            Path to rendered file, or None if rendering failed
        """
        # Try CLI first if available
        if self._cli_available:
            return self._render_cli(mermaid_syntax, filename, format)
        
        # Fall back to API
        return self._render_api(mermaid_syntax, filename, format)
    
    def _render_cli(
        self,
        mermaid_syntax: str,
        filename: str,
        format: str
    ) -> Optional[Path]:
        """Render using mermaid-cli (mmdc or npx)."""
        try:
            input_file = self.output_dir / f"{filename}.mmd"
            output_file = self.output_dir / f"{filename}.{format}"
            
            # Write mermaid syntax to temp file
            input_file.write_text(mermaid_syntax)
            
            # Try mmdc first
            cmd = [
                "mmdc",
                "-i", str(input_file),
                "-o", str(output_file),
                "-t", "default"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30
            )
            
            if result.returncode != 0:
                # Try npx as fallback
                cmd = [
                    "npx",
                    "@mermaid-js/mermaid-cli",
                    "-i", str(input_file),
                    "-o", str(output_file)
                ]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=60  # npx might take longer
                )
            
            if result.returncode == 0 and output_file.exists():
                # Clean up temp file
                input_file.unlink()
                return output_file
            else:
                print(f"CLI rendering failed: {result.stderr.decode() if result.stderr else 'Unknown error'}")
                return None
                
        except Exception as e:
            print(f"CLI rendering failed: {e}")
            return None
    
    def _render_api(
        self,
        mermaid_syntax: str,
        filename: str,
        format: str
    ) -> Optional[Path]:
        """Render using mermaid.ink API."""
        try:
            # Encode mermaid syntax in base64
            encoded = base64.urlsafe_b64encode(
                mermaid_syntax.encode()
            ).decode().rstrip("=")  # Remove padding
            
            # Construct proper mermaid.ink URL
            # Format: https://mermaid.ink/{format}/{base64_encoded_diagram}
            format_map = {
                "png": "png",
                "svg": "svg",
                "pdf": "pdf"
            }
            
            api_format = format_map.get(format, "svg")
            url = f"{self.MERMAID_API_BASE}/{api_format}/{encoded}"
            
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
    
    def render_erd(
        self,
        schema: Dict,
        output_format: str = "svg",
        filename: str = "database_erd"
    ) -> Optional[Path]:
        """
        Render Entity-Relationship Diagram.
        
        Args:
            schema: Database schema dictionary
            output_format: Output format (png, svg, pdf)
            filename: Output filename
            
        Returns:
            Path to rendered diagram
        """
        from .mermaid_gen import generate_mermaid_erd
        
        mermaid_syntax = generate_mermaid_erd(schema)
        return self.render_to_file(mermaid_syntax, filename, output_format)
    
    def render_flowchart(
        self,
        schema: Dict,
        output_format: str = "svg",
        filename: str = "database_flowchart"
    ) -> Optional[Path]:
        """
        Render relationship flowchart.
        
        Args:
            schema: Database schema dictionary
            output_format: Output format (png, svg, pdf)
            filename: Output filename
            
        Returns:
            Path to rendered diagram
        """
        from .mermaid_gen import generate_mermaid_flowchart
        
        mermaid_syntax = generate_mermaid_flowchart(schema)
        return self.render_to_file(mermaid_syntax, filename, output_format)
    
    def get_diagram_path(self, filename: str) -> Path:
        """Get full path for a diagram file."""
        return self.output_dir / filename


def render_database_diagrams(
    schema: Dict,
    output_dir: str = "diagrams",
    formats: list = ["svg", "png"]
) -> Dict[str, Path]:
    """
    Render all database diagrams.
    
    Args:
        schema: Database schema
        output_dir: Output directory
        formats: List of formats to render (svg, png, pdf)
        
    Returns:
        Dictionary mapping diagram names to file paths
    """
    renderer = DiagramRenderer(output_dir)
    results = {}
    
    for format in formats:
        # Render ERD
        erd_path = renderer.render_erd(schema, format, f"erd_{format}")
        if erd_path:
            results[f"erd_{format}"] = erd_path
        
        # Render Flowchart
        flowchart_path = renderer.render_flowchart(
            schema, format, f"flowchart_{format}"
        )
        if flowchart_path:
            results[f"flowchart_{format}"] = flowchart_path
    
    return results
