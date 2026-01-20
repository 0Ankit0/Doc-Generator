"""
Documentation Generator Module

Generates comprehensive technical documentation using AI.
"""

import json
from typing import Optional

from ..config import Config, get_config
from ..analyzers.project_analyzer import ProjectAnalysis, ProjectAnalyzer
from .ai_client import get_ai_client, SYSTEM_PROMPT, DOCUMENTATION_PROMPT


class DocumentationGenerator:
    """Generates comprehensive technical documentation."""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.ai_client = get_ai_client(config)
    
    def generate(self, analysis: ProjectAnalysis, analyzer: ProjectAnalyzer) -> str:
        """Generate comprehensive documentation using AI."""
        # Prepare data for the prompt
        model_data = self._prepare_model_summary(analysis)
        relationships = self._prepare_relationships(analysis)
        patterns = analyzer.detect_patterns()
        
        # Build the prompt
        prompt = DOCUMENTATION_PROMPT.format(
            model_data=model_data,
            relationships=relationships,
            patterns=json.dumps(patterns, indent=2),
        )
        
        # Generate using AI
        return self.ai_client.generate(prompt, SYSTEM_PROMPT)
    
    def generate_simple(self, analysis: ProjectAnalysis, analyzer: ProjectAnalyzer) -> str:
        """Generate documentation without AI."""
        lines = []
        
        # Title
        lines.append("# Project Documentation")
        lines.append("")
        
        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Total Apps**: {len(analysis.apps)}")
        lines.append(f"- **Total Models**: {analysis.total_models}")
        lines.append(f"- **Total Fields**: {analysis.total_fields}")
        lines.append(f"- **Total Relationships**: {analysis.total_relationships}")
        lines.append("")
        
        # Core entities
        core = analyzer.identify_core_entities()
        if core:
            lines.append("### Core Entities")
            lines.append("")
            lines.append("The following models are central to the system (by relationship count):")
            lines.append("")
            for entity in core[:5]:
                lines.append(f"- `{entity}`")
            lines.append("")
        
        # Pattern detection
        patterns = analyzer.detect_patterns()
        if any(patterns.values()):
            lines.append("### Detected Patterns")
            lines.append("")
            
            if patterns["audit_models"]:
                lines.append("**Audit Trail Models** (with created_at/updated_at):")
                for m in patterns["audit_models"][:5]:
                    lines.append(f"- `{m}`")
                lines.append("")
            
            if patterns["soft_delete"]:
                lines.append("**Soft Delete Models** (with is_deleted/deleted_at):")
                for m in patterns["soft_delete"]:
                    lines.append(f"- `{m}`")
                lines.append("")
            
            if patterns["status_workflow"]:
                lines.append("**Status Workflow Models** (with status field):")
                for m in patterns["status_workflow"]:
                    lines.append(f"- `{m}`")
                lines.append("")
            
            if patterns["hierarchical"]:
                lines.append("**Hierarchical Models** (self-referential):")
                for m in patterns["hierarchical"]:
                    lines.append(f"- `{m}`")
                lines.append("")
        
        # Apps documentation
        lines.append("## Applications")
        lines.append("")
        
        for app in analysis.apps:
            lines.append(f"### {app.name.title()}")
            lines.append("")
            lines.append(f"Contains {len(app.models)} model(s):")
            lines.append("")
            
            for model in app.models:
                lines.append(f"#### {model.name}")
                lines.append("")
                
                if model.docstring:
                    lines.append(f"> {model.docstring[:200]}")
                    lines.append("")
                
                lines.append("**Fields:**")
                lines.append("")
                lines.append("| Field | Type | Constraints |")
                lines.append("|-------|------|-------------|")
                
                for field in model.fields:
                    constraints = []
                    if field.is_primary_key:
                        constraints.append("PK")
                    if field.is_foreign_key:
                        constraints.append(f"FK → {field.related_model}")
                    if field.is_many_to_many:
                        constraints.append(f"M2M → {field.related_model}")
                    if field.unique:
                        constraints.append("unique")
                    if not field.null:
                        constraints.append("required")
                    
                    constraint_str = ", ".join(constraints) if constraints else "-"
                    lines.append(f"| {field.name} | {field.field_type} | {constraint_str} |")
                
                lines.append("")
                
                if model.methods:
                    lines.append("**Custom Methods:**")
                    for method in model.methods[:10]:
                        lines.append(f"- `{method}()`")
                    lines.append("")
        
        # Relationships
        if analysis.relationships:
            lines.append("## Relationships")
            lines.append("")
            lines.append("| Source | Target | Type | Field |")
            lines.append("|--------|--------|------|-------|")
            
            for rel in analysis.relationships:
                lines.append(
                    f"| {rel.source_model} | {rel.target_model} | "
                    f"{rel.relationship_type} | {rel.field_name} |"
                )
            lines.append("")
        
        return "\n".join(lines)
    
    def _prepare_model_summary(self, analysis: ProjectAnalysis) -> str:
        """Prepare a summary of models for the prompt."""
        output = []
        
        for app in analysis.apps:
            output.append(f"### App: {app.name}")
            output.append(f"Models: {len(app.models)}")
            
            for model in app.models:
                output.append(f"\n**{model.name}**")
                if model.docstring:
                    output.append(f"  {model.docstring[:150]}")
                
                output.append(f"  Fields: {len(model.fields)}")
                output.append(f"  Methods: {', '.join(model.methods[:5])}")
            
            output.append("")
        
        return "\n".join(output)
    
    def _prepare_relationships(self, analysis: ProjectAnalysis) -> str:
        """Prepare relationships summary for the prompt."""
        if not analysis.relationships:
            return "No relationships found."
        
        lines = []
        for rel in analysis.relationships:
            lines.append(
                f"- {rel.source_model} → {rel.target_model} "
                f"({rel.relationship_type} via {rel.field_name})"
            )
        
        return "\n".join(lines)


def generate_documentation(
    analysis: ProjectAnalysis,
    analyzer: Optional[ProjectAnalyzer] = None,
    use_ai: bool = True,
) -> str:
    """Generate documentation from project analysis."""
    generator = DocumentationGenerator()
    
    if analyzer is None:
        from ..analyzers.project_analyzer import ProjectAnalyzer as PA
        analyzer = PA(analysis.models)
    
    if use_ai:
        return generator.generate(analysis, analyzer)
    return generator.generate_simple(analysis, analyzer)
