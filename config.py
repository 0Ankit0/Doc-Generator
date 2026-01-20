"""
Configuration settings for the Django Documentation Generator.
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class OutputFormat(Enum):
    """Supported output formats for diagrams."""
    MERMAID = "mermaid"
    PLANTUML = "plantuml"


class DiscoveryMode(Enum):
    """Model discovery modes."""
    DJANGO = "django"  # Use Django's app registry (requires Django initialization)
    AST = "ast"  # Use AST parsing (standalone, no Django required)


@dataclass
class Config:
    """Configuration for the documentation generator."""
    
    # Django settings module (for DJANGO mode)
    django_settings_module: Optional[str] = None
    
    # Project directory (for AST mode)
    project_dir: str = "."
    
    # Discovery mode
    discovery_mode: DiscoveryMode = DiscoveryMode.DJANGO
    
    # Output settings
    output_dir: str = "./docs/generated"
    output_format: OutputFormat = OutputFormat.MERMAID
    
    # AI settings
    ai_provider: str = "gemini"
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    
    # Model to use for generation
    ai_model: str = "gemini-2.0-flash"
    
    # Exclusion patterns
    exclude_apps: list = field(default_factory=lambda: [
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.messages",
        "django.contrib.staticfiles",
    ])
    
    # Include Django's built-in models in analysis
    include_builtins: bool = False
    
    def __post_init__(self):
        """Load configuration from environment variables."""
        # Django settings
        if not self.django_settings_module:
            self.django_settings_module = os.environ.get("DJANGO_SETTINGS_MODULE")
        
        # API keys
        if not self.gemini_api_key:
            self.gemini_api_key = os.environ.get("GEMINI_API_KEY")
        
        if not self.openai_api_key:
            self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        
        # Output directory
        env_output_dir = os.environ.get("DOC_OUTPUT_DIR")
        if env_output_dir:
            self.output_dir = env_output_dir
        
        # Discovery mode
        env_mode = os.environ.get("DOC_MODE")
        if env_mode:
            self.discovery_mode = DiscoveryMode(env_mode.lower())
        
        # Output format
        env_format = os.environ.get("DOC_FORMAT")
        if env_format:
            self.output_format = OutputFormat(env_format.lower())
    
    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if self.discovery_mode == DiscoveryMode.DJANGO:
            if not self.django_settings_module:
                errors.append(
                    "Django settings module is required for DJANGO mode. "
                    "Set --settings or DJANGO_SETTINGS_MODULE environment variable."
                )
        
        if self.discovery_mode == DiscoveryMode.AST:
            if not os.path.isdir(self.project_dir):
                errors.append(f"Project directory does not exist: {self.project_dir}")
        
        if self.ai_provider == "gemini" and not self.gemini_api_key:
            errors.append(
                "Gemini API key is required. "
                "Set GEMINI_API_KEY environment variable."
            )
        
        if self.ai_provider == "openai" and not self.openai_api_key:
            errors.append(
                "OpenAI API key is required. "
                "Set OPENAI_API_KEY environment variable."
            )
        
        return errors


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config
