from dataclasses import dataclass, field
import os
from pathlib import Path

SUPPORTED_DOC_TYPES = {
    "overview",
    "architecture",
    "dfd",
    "sequence",
    "flowchart",
    "requirements",
    "components",
    "deployment",
}


@dataclass
class Config:
    project_dir: str = "."
    output_dir: str = "./docs/generated"
    ai_provider: str = "gemini"
    ai_model: str = "gemini-2.0-flash"
    include_patterns: list[str] = field(default_factory=list)
    exclude_patterns: list[str] = field(default_factory=lambda: [
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "node_modules",
        "dist",
        "build",
        ".mypy_cache",
        ".pytest_cache",
    ])
    max_files: int = 1500
    docs_to_generate: list[str] = field(default_factory=lambda: [
        "overview",
        "architecture",
        "dfd",
        "sequence",
        "flowchart",
        "requirements",
    ])
    gemini_api_key: str | None = None
    openai_api_key: str | None = None

    def __post_init__(self):
        if not self.gemini_api_key:
            self.gemini_api_key = os.environ.get("GEMINI_API_KEY")
        if not self.openai_api_key:
            self.openai_api_key = os.environ.get("OPENAI_API_KEY")

    def validate(self, use_ai: bool = True) -> list[str]:
        errors: list[str] = []
        if not Path(self.project_dir).exists():
            errors.append(f"Project directory does not exist: {self.project_dir}")
        unsupported = [doc for doc in self.docs_to_generate if doc not in SUPPORTED_DOC_TYPES]
        if unsupported:
            errors.append(
                "Unsupported document types requested: "
                + ", ".join(sorted(set(unsupported)))
                + ". Supported values are: "
                + ", ".join(sorted(SUPPORTED_DOC_TYPES))
            )
        if use_ai and self.ai_provider == "gemini" and not self.gemini_api_key:
            errors.append("Missing GEMINI_API_KEY for Gemini provider.")
        if use_ai and self.ai_provider == "openai" and not self.openai_api_key:
            errors.append("Missing OPENAI_API_KEY for OpenAI provider.")
        return errors
