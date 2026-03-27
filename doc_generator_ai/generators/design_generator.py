"""Design document generation orchestration."""

from __future__ import annotations

from ..config import Config
from ..discovery.project_structure import ProjectStructure
from ..analyzers.system_analyzer import SystemAnalysis
from .ai_client import get_ai_client, build_prompt, SYSTEM_PROMPT


class DesignGenerator:
    def __init__(self, config: Config):
        self.config = config
        self.ai_client = get_ai_client(config)

    def generate(self, doc_type: str, structure: ProjectStructure, analysis: SystemAnalysis, requirements: str = "") -> str:
        prompt = build_prompt(doc_type, structure.to_dict(), analysis.to_dict(), requirements)
        return self.ai_client.generate(prompt, SYSTEM_PROMPT).strip()

    def generate_simple(self, doc_type: str, structure: ProjectStructure, analysis: SystemAnalysis, requirements: str = "") -> str:
        if doc_type in {"dfd", "flowchart"}:
            return self._simple_flow(analysis.project_name)
        if doc_type == "sequence":
            return self._simple_sequence(analysis.project_name)
        if doc_type == "architecture":
            return self._simple_architecture(analysis, requirements)
        if doc_type == "requirements":
            return self._simple_requirements(requirements)
        if doc_type == "components":
            return self._simple_components(analysis)
        if doc_type == "deployment":
            return self._simple_deployment(analysis, requirements)
        return self._simple_overview(analysis)

    def _simple_overview(self, analysis: SystemAnalysis) -> str:
        lines = [
            f"# {analysis.project_name} - System Overview",
            "",
            f"- Total files: **{analysis.total_files}**",
            f"- Total directories: **{analysis.total_directories}**",
            f"- Python symbols discovered: **{analysis.python_symbol_count}**",
            "",
            "## Main File Types",
        ]
        for ext, count in list(analysis.file_types.items())[:10]:
            lines.append(f"- `{ext}`: {count}")
        if analysis.top_directories:
            lines.extend(["", "## Top-Level Areas"])
            lines.extend(f"- `{d}`" for d in analysis.top_directories[:10])
        return "\n".join(lines)

    def _simple_architecture(self, analysis: SystemAnalysis, requirements: str) -> str:
        return "\n".join([
            "# Architecture Document",
            "",
            "## Identified Layers",
            *[f"- **{k}**: {', '.join(v[:5])}" for k, v in analysis.likely_layers.items()],
            "",
            "## Notes",
            requirements or "No extra requirements provided.",
        ])

    def _simple_requirements(self, requirements: str) -> str:
        return "\n".join([
            "# Requirements",
            "",
            "## Functional Requirements",
            "- Generate docs from repository structure.",
            "- Support multiple output doc types.",
            "",
            "## User Constraints",
            requirements or "No additional constraints provided.",
        ])

    def _simple_flow(self, project_name: str) -> str:
        return "\n".join([
            "flowchart TD",
            f"    A[Scan {project_name} file structure] --> B[Analyze architecture hints]",
            "    B --> C[Generate selected docs]",
            "    C --> D[Write markdown outputs]",
            "    D --> E[Review and iterate]",
        ])

    def _simple_sequence(self, project_name: str) -> str:
        return "\n".join([
            "sequenceDiagram",
            "    participant U as User",
            "    participant G as Doc Generator",
            "    participant FS as File System",
            "    participant AI as AI Provider",
            "    U->>G: Request selected docs",
            "    G->>FS: Scan project structure",
            "    FS-->>G: Files + folders + symbols",
            "    G->>AI: Prompt per doc type",
            "    AI-->>G: Generated content",
            "    G-->>U: Markdown documents",
        ])

    def _simple_components(self, analysis: SystemAnalysis) -> str:
        lines = [
            "# Component Design",
            "",
            "## Candidate Components",
        ]
        for layer, folders in analysis.likely_layers.items():
            lines.append(f"### {layer.title()} Layer")
            for folder in folders[:5]:
                lines.append(f"- `{folder}`")
            lines.append("")
        if len(lines) <= 4:
            lines.append("- No clear layer directories were inferred from folder names.")
        return "\n".join(lines)

    def _simple_deployment(self, analysis: SystemAnalysis, requirements: str) -> str:
        return "\n".join([
            "# Deployment & Operations",
            "",
            "## Suggested Runtime Topology",
            "- Stateless application service",
            "- Persistent data store",
            "- Background worker for asynchronous jobs",
            "",
            "## Operational Recommendations",
            "- Add health checks and readiness probes.",
            "- Add centralized logs, metrics, and tracing.",
            "- Define CI/CD with rollback strategy.",
            "",
            "## Context",
            requirements or f"Derived from project `{analysis.project_name}`.",
        ])
