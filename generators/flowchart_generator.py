"""
Flowchart Generator Module

Generates process flowcharts from model analysis using AI.
"""

import json
from typing import Optional

from ..config import Config, get_config
from ..analyzers.project_analyzer import ProjectAnalysis, ProjectAnalyzer
from .ai_client import get_ai_client, SYSTEM_PROMPT, FLOWCHART_PROMPT


class FlowchartGenerator:
    """Generates process flowcharts from project analysis."""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.ai_client = get_ai_client(config)
    
    def generate(self, analysis: ProjectAnalysis, analyzer: ProjectAnalyzer) -> str:
        """Generate flowcharts using AI."""
        # Prepare data for the prompt
        model_data = self._prepare_model_data(analysis)
        patterns = analyzer.detect_patterns()
        core_entities = analyzer.identify_core_entities()
        
        # Build the prompt
        prompt = FLOWCHART_PROMPT.format(
            model_data=model_data,
            patterns=json.dumps(patterns, indent=2),
            core_entities="\n".join(f"- {e}" for e in core_entities),
        )
        
        # Generate using AI
        result = self.ai_client.generate(prompt, SYSTEM_PROMPT)
        
        return self._format_result(result)
    
    def generate_crud_flowchart(self, model_name: str) -> str:
        """Generate a standard CRUD flowchart for a model."""
        safe_name = model_name.replace(".", "_").replace(" ", "_")
        
        return f"""flowchart TD
    Start([Start]) --> Action{{Action Type?}}
    
    Action -->|Create| C1[Validate Input]
    C1 --> C2{{Valid?}}
    C2 -->|Yes| C3[Create {model_name}]
    C2 -->|No| C4[Return Errors]
    C3 --> Success([Success])
    C4 --> Start
    
    Action -->|Read| R1[Query Database]
    R1 --> R2{{Found?}}
    R2 -->|Yes| R3[Return Data]
    R2 -->|No| R4[Return 404]
    R3 --> Success
    R4 --> Start
    
    Action -->|Update| U1[Find {model_name}]
    U1 --> U2{{Exists?}}
    U2 -->|Yes| U3[Validate Changes]
    U2 -->|No| R4
    U3 --> U4{{Valid?}}
    U4 -->|Yes| U5[Update {model_name}]
    U4 -->|No| C4
    U5 --> Success
    
    Action -->|Delete| D1[Find {model_name}]
    D1 --> D2{{Exists?}}
    D2 -->|Yes| D3[Delete {model_name}]
    D2 -->|No| R4
    D3 --> Success"""
    
    def generate_workflow_flowchart(self, model_name: str) -> str:
        """
        Generate a status workflow flowchart for models with status fields.
        """
        return f"""flowchart TD
    Start([New {model_name}]) --> Draft[Draft Status]
    Draft --> Submit{{Submit for Review?}}
    Submit -->|Yes| Pending[Pending Review]
    Submit -->|No| Draft
    
    Pending --> Review{{Review Outcome}}
    Review -->|Approved| Approved[Approved Status]
    Review -->|Rejected| Rejected[Rejected Status]
    Review -->|Needs Changes| Draft
    
    Approved --> Active[Active/Published]
    Rejected --> End1([Closed])
    
    Active --> Archive{{Archive?}}
    Archive -->|Yes| Archived[Archived Status]
    Archive -->|No| Active
    
    Archived --> End2([Archived])"""
    
    def generate_simple(self, analysis: ProjectAnalysis, analyzer: ProjectAnalyzer) -> str:
        """Generate simple flowcharts without AI."""
        patterns = analyzer.detect_patterns()
        result = []
        
        # Generate CRUD flowchart for core entities
        core_entities = analyzer.identify_core_entities()[:3]
        
        if core_entities:
            result.append("## Core Entity CRUD Operations")
            result.append("")
            result.append("```mermaid")
            result.append(self.generate_crud_flowchart(core_entities[0].split(".")[-1]))
            result.append("```")
            result.append("")
        
        # Generate workflow flowchart if status patterns detected
        if patterns.get("status_workflow"):
            model_name = patterns["status_workflow"][0].split(".")[-1]
            result.append(f"## {model_name} Status Workflow")
            result.append("")
            result.append("```mermaid")
            result.append(self.generate_workflow_flowchart(model_name))
            result.append("```")
        
        return "\n".join(result)
    
    def _prepare_model_data(self, analysis: ProjectAnalysis) -> str:
        """Prepare model data as formatted text for the prompt."""
        return json.dumps(analysis.to_dict(), indent=2)
    
    def _format_result(self, text: str) -> str:
        """Format the AI result with proper markdown."""
        # Clean up any extra code blocks and format nicely
        lines = text.strip().split("\n")
        result = []
        in_code_block = False
        
        for line in lines:
            # Handle code block markers
            if line.strip().startswith("```mermaid"):
                result.append(line)
                in_code_block = True
            elif line.strip() == "```" and in_code_block:
                result.append(line)
                in_code_block = False
            elif line.strip().startswith("```"):
                # Convert generic code blocks to mermaid
                if "flowchart" in text[text.find(line):text.find(line)+100]:
                    result.append("```mermaid")
                    in_code_block = True
                else:
                    result.append(line)
            else:
                result.append(line)
        
        return "\n".join(result)


def generate_flowcharts(
    analysis: ProjectAnalysis,
    analyzer: Optional[ProjectAnalyzer] = None,
    use_ai: bool = True,
) -> str:
    """Generate flowcharts from project analysis."""
    generator = FlowchartGenerator()
    
    if analyzer is None:
        # Create analyzer from models
        from ..analyzers.project_analyzer import ProjectAnalyzer as PA
        analyzer = PA(analysis.models)
    
    if use_ai:
        return generator.generate(analysis, analyzer)
    return generator.generate_simple(analysis, analyzer)
