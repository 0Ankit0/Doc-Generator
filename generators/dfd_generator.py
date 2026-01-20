"""
Data Flow Diagram Generator Module

Generates DFD diagrams from model analysis using AI.
"""

import json
from typing import Optional

from ..config import Config, get_config
from ..analyzers.project_analyzer import ProjectAnalysis, ProjectAnalyzer
from .ai_client import get_ai_client, SYSTEM_PROMPT, DFD_PROMPT


class DFDGenerator:
    """Generates Data Flow Diagrams from project analysis."""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.ai_client = get_ai_client(config)
    
    def generate(self, analysis: ProjectAnalysis, analyzer: ProjectAnalyzer) -> str:
        """Generate a DFD using AI."""
        # Prepare data for the prompt
        model_data = self._prepare_model_data(analysis)
        patterns = analyzer.detect_patterns()
        
        # Build the prompt
        prompt = DFD_PROMPT.format(
            model_data=model_data,
            patterns=json.dumps(patterns, indent=2),
        )
        
        # Generate using AI
        result = self.ai_client.generate(prompt, SYSTEM_PROMPT)
        
        # Clean up the result
        return self._clean_mermaid(result)
    
    def generate_simple(self, analysis: ProjectAnalysis) -> str:
        """
        Generate a simple DFD without AI.
        Creates a basic data flow showing models as data stores.
        """
        lines = ["flowchart TD"]
        
        # External entities
        lines.append("    User([User])")
        lines.append("    Admin([Admin])")
        lines.append("")
        
        # Data stores (models grouped by app)
        for app in analysis.apps:
            if not app.models:
                continue
            
            lines.append(f"    subgraph {app.name.upper()}[\"{app.name.title()}\"]")
            
            for model in app.models:
                if model.is_abstract:
                    continue
                
                model_id = f"{app.name}_{model.name}".replace(" ", "_")
                lines.append(f"        {model_id}[({model.name})]")
            
            lines.append("    end")
            lines.append("")
        
        # Processes
        lines.append("    Process1{{CRUD Operations}}")
        lines.append("    Process2{{Business Logic}}")
        lines.append("")
        
        # Basic flows
        lines.append("    User --> Process1")
        lines.append("    Admin --> Process1")
        lines.append("    Process1 --> Process2")
        
        # Connect processes to data stores
        for app in analysis.apps:
            for model in app.models:
                if model.is_abstract:
                    continue
                model_id = f"{app.name}_{model.name}".replace(" ", "_")
                lines.append(f"    Process2 --> {model_id}")
        
        return "\n".join(lines)
    
    def _prepare_model_data(self, analysis: ProjectAnalysis) -> str:
        """Prepare model data as formatted text for the prompt."""
        return json.dumps(analysis.to_dict(), indent=2)
    
    def _clean_mermaid(self, text: str) -> str:
        """Clean up Mermaid code from AI response."""
        lines = text.strip().split("\n")
        result = []
        in_code_block = False
        
        for line in lines:
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue
            result.append(line)
        
        text = "\n".join(result).strip()
        
        # Ensure it starts with flowchart
        if not text.startswith("flowchart"):
            if "flowchart" in text:
                idx = text.find("flowchart")
                text = text[idx:]
        
        return text


def generate_dfd(
    analysis: ProjectAnalysis,
    analyzer: Optional[ProjectAnalyzer] = None,
    use_ai: bool = True,
) -> str:
    """Generate a DFD from project analysis."""
    generator = DFDGenerator()
    
    if use_ai and analyzer:
        return generator.generate(analysis, analyzer)
    return generator.generate_simple(analysis)
