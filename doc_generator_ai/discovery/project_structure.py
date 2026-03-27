"""Project structure discovery utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import ast
import fnmatch

from ..config import Config


@dataclass
class CodeSymbol:
    kind: str
    name: str
    line: int


@dataclass
class FileInfo:
    path: str
    extension: str
    symbols: list[CodeSymbol] = field(default_factory=list)


@dataclass
class ProjectStructure:
    root: str
    directories: list[str] = field(default_factory=list)
    files: list[FileInfo] = field(default_factory=list)
    tree_preview: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "root": self.root,
            "directories": self.directories,
            "files": [
                {
                    "path": f.path,
                    "extension": f.extension,
                    "symbols": [s.__dict__ for s in f.symbols],
                }
                for f in self.files
            ],
            "stats": {
                "total_directories": len(self.directories),
                "total_files": len(self.files),
            },
            "tree_preview": self.tree_preview,
        }


class ProjectStructureScanner:
    def __init__(self, config: Config):
        self.config = config

    def scan(self) -> ProjectStructure:
        project_root = Path(self.config.project_dir).resolve()
        result = ProjectStructure(root=str(project_root))

        for path in sorted(project_root.rglob("*")):
            rel = path.relative_to(project_root).as_posix()
            if self._is_excluded(rel):
                continue

            if path.is_dir():
                result.directories.append(rel)
                continue

            if len(result.files) >= self.config.max_files:
                break

            info = FileInfo(path=rel, extension=path.suffix.lower())
            if path.suffix.lower() == ".py":
                info.symbols = self._extract_python_symbols(path)
            result.files.append(info)

        result.tree_preview = self._build_tree_preview(result.directories, result.files)
        return result

    def _is_excluded(self, relative_path: str) -> bool:
        parts = set(relative_path.split("/"))
        if any(part in parts for part in self.config.exclude_patterns):
            return True
        if self.config.include_patterns:
            return not any(fnmatch.fnmatch(relative_path, pattern) for pattern in self.config.include_patterns)
        return False

    def _build_tree_preview(self, directories: list[str], files: list[FileInfo], max_items: int = 120) -> list[str]:
        file_paths = [f.path for f in files]
        combined = sorted(directories + file_paths)
        return combined[:max_items]

    def _extract_python_symbols(self, path: Path) -> list[CodeSymbol]:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except Exception:
            return []

        symbols: list[CodeSymbol] = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                symbols.append(CodeSymbol(kind="class", name=node.name, line=node.lineno))
            elif isinstance(node, ast.FunctionDef):
                symbols.append(CodeSymbol(kind="function", name=node.name, line=node.lineno))
        return symbols[:40]
