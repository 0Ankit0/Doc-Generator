"""Project analysis for system design documentation."""

from collections import Counter
from dataclasses import dataclass

from ..discovery.project_structure import ProjectStructure


@dataclass
class SystemAnalysis:
    project_name: str
    total_files: int
    total_directories: int
    file_types: dict[str, int]
    likely_layers: dict[str, list[str]]
    top_directories: list[str]
    python_symbol_count: int

    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "total_files": self.total_files,
            "total_directories": self.total_directories,
            "file_types": self.file_types,
            "likely_layers": self.likely_layers,
            "top_directories": self.top_directories,
            "python_symbol_count": self.python_symbol_count,
        }


class SystemAnalyzer:
    LAYER_HINTS = {
        "api": ["api", "views", "routes", "urls", "endpoint", "controller"],
        "domain": ["model", "entity", "schema", "core", "service"],
        "data": ["repo", "repository", "db", "database", "storage", "migration"],
        "ui": ["template", "component", "frontend", "static", "ui"],
        "infra": ["deploy", "docker", "k8s", "terraform", "config", "settings"],
    }

    def analyze(self, structure: ProjectStructure) -> SystemAnalysis:
        file_types = Counter(f.extension or "<no_ext>" for f in structure.files)
        top_directories = Counter(d.split("/")[0] for d in structure.directories if d)
        symbol_count = sum(len(f.symbols) for f in structure.files)

        layers: dict[str, list[str]] = {layer: [] for layer in self.LAYER_HINTS}
        for d in structure.directories:
            lower = d.lower()
            for layer, hints in self.LAYER_HINTS.items():
                if any(h in lower for h in hints):
                    layers[layer].append(d)

        return SystemAnalysis(
            project_name=structure.root.rstrip("/").split("/")[-1],
            total_files=len(structure.files),
            total_directories=len(structure.directories),
            file_types=dict(file_types.most_common()),
            likely_layers={k: v[:20] for k, v in layers.items() if v},
            top_directories=[d for d, _ in top_directories.most_common(15)],
            python_symbol_count=symbol_count,
        )
