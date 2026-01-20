"""
Model Discovery Module

Discovers Django models using either Django's app registry or AST parsing.
"""

import ast
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from ..config import Config, DiscoveryMode, get_config


@dataclass
class FieldInfo:
    """Information about a model field."""
    name: str
    field_type: str
    is_primary_key: bool = False
    is_foreign_key: bool = False
    is_many_to_many: bool = False
    is_one_to_one: bool = False
    related_model: Optional[str] = None
    max_length: Optional[int] = None
    null: bool = False
    blank: bool = False
    default: Optional[Any] = None
    choices: Optional[list] = None
    help_text: Optional[str] = None
    verbose_name: Optional[str] = None
    unique: bool = False
    db_index: bool = False
    

@dataclass
class ModelInfo:
    """Information about a Django model."""
    name: str
    app_label: str
    module: str
    fields: list[FieldInfo] = field(default_factory=list)
    meta_options: dict = field(default_factory=dict)
    docstring: Optional[str] = None
    is_abstract: bool = False
    parent_models: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    
    @property
    def full_name(self) -> str:
        """Get the fully qualified model name."""
        return f"{self.app_label}.{self.name}"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "app_label": self.app_label,
            "module": self.module,
            "full_name": self.full_name,
            "docstring": self.docstring,
            "is_abstract": self.is_abstract,
            "parent_models": self.parent_models,
            "methods": self.methods,
            "meta_options": self.meta_options,
            "fields": [
                {
                    "name": f.name,
                    "field_type": f.field_type,
                    "is_primary_key": f.is_primary_key,
                    "is_foreign_key": f.is_foreign_key,
                    "is_many_to_many": f.is_many_to_many,
                    "is_one_to_one": f.is_one_to_one,
                    "related_model": f.related_model,
                    "max_length": f.max_length,
                    "null": f.null,
                    "blank": f.blank,
                    "unique": f.unique,
                    "db_index": f.db_index,
                    "help_text": f.help_text,
                    "verbose_name": f.verbose_name,
                }
                for f in self.fields
            ],
        }


class DjangoModelFinder:
    """Discovers models using Django's app registry."""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self._django_initialized = False
    
    def _init_django(self) -> None:
        """Initialize Django if not already initialized."""
        if self._django_initialized:
            return
        
        if self.config.django_settings_module:
            os.environ.setdefault(
                "DJANGO_SETTINGS_MODULE",
                self.config.django_settings_module
            )
        
        import django
        django.setup()
        self._django_initialized = True
    
    def discover(self) -> list[ModelInfo]:
        """Discover all models in the Django project."""
        self._init_django()
        
        from django.apps import apps
        from django.db import models as django_models
        
        discovered_models = []
        
        for model in apps.get_models():
            app_label = model._meta.app_label
            
            # Check exclusions
            app_full_name = f"{model.__module__.rsplit('.', 1)[0]}"
            if not self.config.include_builtins:
                if any(
                    app_full_name.startswith(excluded.replace(".", ""))
                    or app_label in excluded
                    for excluded in self.config.exclude_apps
                ):
                    # Check if it's a Django built-in
                    if model.__module__.startswith("django."):
                        continue
            
            model_info = self._extract_model_info(model)
            discovered_models.append(model_info)
        
        return discovered_models
    
    def _extract_model_info(self, model) -> ModelInfo:
        """Extract information from a Django model class."""
        from django.db import models as django_models
        
        meta = model._meta
        
        # Extract fields
        fields = []
        for field in meta.get_fields():
            field_info = self._extract_field_info(field)
            if field_info:
                fields.append(field_info)
        
        # Extract meta options
        meta_options = {
            "verbose_name": str(meta.verbose_name),
            "verbose_name_plural": str(meta.verbose_name_plural),
            "db_table": meta.db_table,
            "ordering": list(meta.ordering) if meta.ordering else [],
            "unique_together": [list(ut) for ut in meta.unique_together],
            "indexes": [idx.name for idx in meta.indexes],
            "abstract": meta.abstract,
        }
        
        # Extract parent models
        parent_models = [
            f"{parent._meta.app_label}.{parent.__name__}"
            for parent in model.__mro__[1:]
            if hasattr(parent, "_meta") and parent != django_models.Model
        ]
        
        # Extract methods (only custom ones, not inherited from Model)
        methods = []
        for name in dir(model):
            if name.startswith("_"):
                continue
            attr = getattr(model, name, None)
            if callable(attr) and not hasattr(django_models.Model, name):
                methods.append(name)
        
        return ModelInfo(
            name=model.__name__,
            app_label=meta.app_label,
            module=model.__module__,
            fields=fields,
            meta_options=meta_options,
            docstring=model.__doc__,
            is_abstract=meta.abstract,
            parent_models=parent_models,
            methods=methods,
        )
    
    def _extract_field_info(self, field) -> Optional[FieldInfo]:
        """Extract information from a Django model field."""
        from django.db.models import fields as django_fields
        from django.db.models.fields import related as related_fields
        
        # Skip reverse relations
        if hasattr(field, "field"):
            return None
        
        field_type = type(field).__name__
        
        # Determine relationship type
        is_fk = isinstance(field, related_fields.ForeignKey)
        is_m2m = isinstance(field, related_fields.ManyToManyField)
        is_o2o = isinstance(field, related_fields.OneToOneField)
        
        # Get related model name
        related_model = None
        if is_fk or is_m2m or is_o2o:
            if hasattr(field, "related_model") and field.related_model:
                related_model = (
                    f"{field.related_model._meta.app_label}."
                    f"{field.related_model.__name__}"
                )
        
        # Extract common attributes
        return FieldInfo(
            name=field.name,
            field_type=field_type,
            is_primary_key=getattr(field, "primary_key", False),
            is_foreign_key=is_fk,
            is_many_to_many=is_m2m,
            is_one_to_one=is_o2o,
            related_model=related_model,
            max_length=getattr(field, "max_length", None),
            null=getattr(field, "null", False),
            blank=getattr(field, "blank", False),
            unique=getattr(field, "unique", False),
            db_index=getattr(field, "db_index", False),
            help_text=str(getattr(field, "help_text", "") or ""),
            verbose_name=str(getattr(field, "verbose_name", "") or ""),
        )


class ASTModelFinder:
    """Discovers models using AST parsing (no Django required)."""
    
    # Common Django field types
    FIELD_TYPES = {
        "CharField", "TextField", "IntegerField", "FloatField", "DecimalField",
        "BooleanField", "DateField", "DateTimeField", "TimeField", "EmailField",
        "URLField", "UUIDField", "FileField", "ImageField", "SlugField",
        "PositiveIntegerField", "PositiveSmallIntegerField", "SmallIntegerField",
        "BigIntegerField", "AutoField", "BigAutoField", "BinaryField",
        "DurationField", "GenericIPAddressField", "IPAddressField", "JSONField",
    }
    
    RELATION_FIELDS = {
        "ForeignKey": "is_foreign_key",
        "ManyToManyField": "is_many_to_many",
        "OneToOneField": "is_one_to_one",
    }
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
    
    def discover(self) -> list[ModelInfo]:
        """Discover all models by parsing Python files."""
        project_dir = Path(self.config.project_dir).resolve()
        discovered_models = []
        
        # Find all models.py files
        for models_file in project_dir.rglob("models.py"):
            # Skip migrations and tests directories
            parts = models_file.parts
            if "migrations" in parts or "tests" in parts:
                continue
            # Also skip test files (test_*.py)
            if models_file.name.startswith("test_"):
                continue
            
            app_models = self._parse_models_file(models_file)
            discovered_models.extend(app_models)
        
        # Also check models/ directories
        for models_init in project_dir.rglob("models/__init__.py"):
            if "migrations" in str(models_init):
                continue
            
            models_dir = models_init.parent
            for py_file in models_dir.glob("*.py"):
                if py_file.name == "__init__.py":
                    continue
                app_models = self._parse_models_file(py_file)
                discovered_models.extend(app_models)
        
        return discovered_models
    
    def _parse_models_file(self, file_path: Path) -> list[ModelInfo]:
        """Parse a models.py file and extract model information."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
            return []
        
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            print(f"Warning: Syntax error in {file_path}: {e}")
            return []
        
        # Determine app label from path
        app_label = file_path.parent.name
        if app_label == "models":
            app_label = file_path.parent.parent.name
        
        models = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                model_info = self._parse_class(node, app_label, str(file_path))
                if model_info:
                    models.append(model_info)
        
        return models
    
    def _parse_class(
        self, node: ast.ClassDef, app_label: str, module: str
    ) -> Optional[ModelInfo]:
        """Parse a class definition and determine if it's a Django model."""
        # Check if it inherits from models.Model
        is_model = False
        parent_models = []
        
        for base in node.bases:
            base_name = self._get_name(base)
            if base_name in ("models.Model", "Model"):
                is_model = True
            elif "Model" in base_name and "Mixin" not in base_name:
                parent_models.append(base_name)
        
        if not is_model:
            return None
        
        # Check for abstract in Meta class
        is_abstract = False
        meta_options = {}
        
        for item in node.body:
            if isinstance(item, ast.ClassDef) and item.name == "Meta":
                meta_options, is_abstract = self._parse_meta(item)
                break
        
        # Extract fields
        fields = []
        methods = []
        
        for item in node.body:
            if isinstance(item, ast.Assign):
                field_info = self._parse_field_assignment(item)
                if field_info:
                    fields.append(field_info)
            elif isinstance(item, ast.AnnAssign):
                field_info = self._parse_annotated_field(item)
                if field_info:
                    fields.append(field_info)
            elif isinstance(item, ast.FunctionDef):
                if not item.name.startswith("_"):
                    methods.append(item.name)
        
        # Get docstring
        docstring = ast.get_docstring(node)
        
        return ModelInfo(
            name=node.name,
            app_label=app_label,
            module=module,
            fields=fields,
            meta_options=meta_options,
            docstring=docstring,
            is_abstract=is_abstract,
            parent_models=parent_models,
            methods=methods,
        )
    
    def _parse_meta(self, meta_node: ast.ClassDef) -> tuple[dict, bool]:
        """Parse a Meta class for options."""
        options = {}
        is_abstract = False
        
        for item in meta_node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        if target.id == "abstract":
                            if isinstance(item.value, ast.Constant):
                                is_abstract = item.value.value is True
                        else:
                            options[target.id] = self._get_value(item.value)
        
        return options, is_abstract
    
    def _parse_field_assignment(self, node: ast.Assign) -> Optional[FieldInfo]:
        """Parse a field assignment like: name = models.CharField(...)"""
        if len(node.targets) != 1:
            return None
        
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            return None
        
        field_name = target.id
        
        # Skip private attributes
        if field_name.startswith("_"):
            return None
        
        # Check if it's a field definition
        if not isinstance(node.value, ast.Call):
            return None
        
        call = node.value
        func_name = self._get_name(call.func)
        
        # Extract field type
        field_type = func_name.split(".")[-1] if "." in func_name else func_name
        
        if field_type not in self.FIELD_TYPES and field_type not in self.RELATION_FIELDS:
            return None
        
        # Parse field arguments
        return self._create_field_info(field_name, field_type, call)
    
    def _parse_annotated_field(self, node: ast.AnnAssign) -> Optional[FieldInfo]:
        """Parse an annotated field assignment."""
        if not isinstance(node.target, ast.Name):
            return None
        
        field_name = node.target.id
        
        if node.value is None or not isinstance(node.value, ast.Call):
            return None
        
        call = node.value
        func_name = self._get_name(call.func)
        field_type = func_name.split(".")[-1] if "." in func_name else func_name
        
        if field_type not in self.FIELD_TYPES and field_type not in self.RELATION_FIELDS:
            return None
        
        return self._create_field_info(field_name, field_type, call)
    
    def _create_field_info(
        self, field_name: str, field_type: str, call: ast.Call
    ) -> FieldInfo:
        """Create a FieldInfo from parsed AST data."""
        is_fk = field_type == "ForeignKey"
        is_m2m = field_type == "ManyToManyField"
        is_o2o = field_type == "OneToOneField"
        
        # Get related model from first positional argument
        related_model = None
        if (is_fk or is_m2m or is_o2o) and call.args:
            related_model = self._get_value(call.args[0])
        
        # Parse keyword arguments
        kwargs = {}
        for keyword in call.keywords:
            if keyword.arg:
                kwargs[keyword.arg] = self._get_value(keyword.value)
        
        return FieldInfo(
            name=field_name,
            field_type=field_type,
            is_primary_key=kwargs.get("primary_key", False),
            is_foreign_key=is_fk,
            is_many_to_many=is_m2m,
            is_one_to_one=is_o2o,
            related_model=str(related_model) if related_model else None,
            max_length=kwargs.get("max_length"),
            null=kwargs.get("null", False),
            blank=kwargs.get("blank", False),
            unique=kwargs.get("unique", False),
            db_index=kwargs.get("db_index", False),
            help_text=kwargs.get("help_text"),
            verbose_name=kwargs.get("verbose_name"),
        )
    
    def _get_name(self, node) -> str:
        """Get the name from an AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return ""
    
    def _get_value(self, node) -> Any:
        """Get the value from an AST node."""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, (ast.List, ast.Tuple)):
            return [self._get_value(elt) for elt in node.elts]
        elif isinstance(node, ast.Dict):
            return {
                self._get_value(k): self._get_value(v)
                for k, v in zip(node.keys, node.values)
                if k is not None
            }
        return None


def get_model_finder(config: Optional[Config] = None) -> DjangoModelFinder | ASTModelFinder:
    """Get the appropriate model finder based on configuration."""
    config = config or get_config()
    
    if config.discovery_mode == DiscoveryMode.AST:
        return ASTModelFinder(config)
    return DjangoModelFinder(config)


def discover_models(config: Optional[Config] = None) -> list[ModelInfo]:
    """Discover all models using the configured method."""
    finder = get_model_finder(config)
    return finder.discover()
