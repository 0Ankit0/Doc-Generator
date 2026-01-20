"""
ER Diagram Generator Module

Generates Entity-Relationship diagrams from model analysis.
"""

import json
from typing import Optional

from ..config import Config, get_config
from ..analyzers.project_analyzer import ProjectAnalysis
from .ai_client import get_ai_client, SYSTEM_PROMPT, ER_DIAGRAM_PROMPT


class ERDiagramGenerator:
    """Generates ER diagrams from project analysis."""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.ai_client = get_ai_client(config)
    
    def generate(self, analysis: ProjectAnalysis) -> str:
        """Generate an ER diagram using AI."""
        # Prepare model data for the prompt
        model_data = self._prepare_model_data(analysis)
        
        # Build the prompt
        prompt = ER_DIAGRAM_PROMPT.format(model_data=model_data)
        
        # Generate using AI
        result = self.ai_client.generate(prompt, SYSTEM_PROMPT)
        
        # Clean up the result
        return self._clean_mermaid(result)
    
    def generate_simple(self, analysis: ProjectAnalysis) -> str:
        """
        Generate a simple ER diagram without AI.
        Uses direct Mermaid generation from model data.
        """
        lines = ["erDiagram"]
        
        # Generate entity definitions
        for model in analysis.models:
            if model.is_abstract:
                continue
                
            entity_name = model.name.replace(" ", "_")
            lines.append(f"    {entity_name} {{")
            
            for field in model.fields:
                field_type = self._map_field_type(field.field_type)
                pk_marker = " PK" if field.is_primary_key else ""
                fk_marker = " FK" if field.is_foreign_key else ""
                lines.append(f"        {field_type} {field.name}{pk_marker}{fk_marker}")
            
            lines.append("    }")
        
        # Generate relationships
        for rel in analysis.relationships:
            source = rel.source_model.split(".")[-1].replace(" ", "_")
            target = rel.target_model.split(".")[-1].replace(" ", "_")
            
            if rel.relationship_type == "many-to-one":
                cardinality = "}o--||"
            elif rel.relationship_type == "one-to-one":
                cardinality = "||--||"
            elif rel.relationship_type == "many-to-many":
                cardinality = "}o--o{"
            else:
                cardinality = "--"
            
            lines.append(f"    {source} {cardinality} {target} : {rel.field_name}")
        
        return "\n".join(lines)
    
    def _prepare_model_data(self, analysis: ProjectAnalysis) -> str:
        """Prepare model data as formatted text for the prompt."""
        output = []
        
        for app in analysis.apps:
            output.append(f"### App: {app.name}")
            
            for model in app.models:
                output.append(f"\n**{model.name}**")
                if model.docstring:
                    output.append(f"  Description: {model.docstring[:200]}")
                
                output.append("  Fields:")
                for field in model.fields:
                    attrs = []
                    if field.is_primary_key:
                        attrs.append("PK")
                    if field.is_foreign_key:
                        attrs.append(f"FK → {field.related_model}")
                    if field.is_many_to_many:
                        attrs.append(f"M2M → {field.related_model}")
                    if field.unique:
                        attrs.append("unique")
                    if not field.null:
                        attrs.append("required")
                    
                    attr_str = f" ({', '.join(attrs)})" if attrs else ""
                    output.append(f"    - {field.name}: {field.field_type}{attr_str}")
            
            output.append("")
        
        return "\n".join(output)
    
    def _map_field_type(self, django_type: str) -> str:
        """Map Django field types to simpler ER types."""
        type_mapping = {
            "CharField": "string",
            "TextField": "text",
            "IntegerField": "int",
            "BigIntegerField": "bigint",
            "SmallIntegerField": "smallint",
            "PositiveIntegerField": "int",
            "FloatField": "float",
            "DecimalField": "decimal",
            "BooleanField": "bool",
            "DateField": "date",
            "DateTimeField": "datetime",
            "TimeField": "time",
            "UUIDField": "uuid",
            "EmailField": "string",
            "URLField": "string",
            "SlugField": "string",
            "FileField": "string",
            "ImageField": "string",
            "JSONField": "json",
            "AutoField": "int",
            "BigAutoField": "bigint",
            "ForeignKey": "int",
            "OneToOneField": "int",
            "ManyToManyField": "m2m",
        }
        return type_mapping.get(django_type, "string")
    
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
        
        # Ensure it starts with erDiagram
        if not text.startswith("erDiagram"):
            # Try to find erDiagram in the text
            if "erDiagram" in text:
                idx = text.find("erDiagram")
                text = text[idx:]
        
        return text


def generate_er_diagram(analysis: ProjectAnalysis, use_ai: bool = True) -> str:
    """Generate an ER diagram from project analysis."""
    generator = ERDiagramGenerator()
    
    if use_ai:
        return generator.generate(analysis)
    return generator.generate_simple(analysis)
