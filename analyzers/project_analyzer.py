"""
Project Analyzer Module

Provides high-level analysis of the entire Django project structure,
including relationships between models and data flow patterns.
"""

from dataclasses import dataclass, field
from typing import Optional

from ..discovery.model_finder import ModelInfo, FieldInfo


@dataclass
class RelationshipInfo:
    """Information about a relationship between models."""
    source_model: str
    target_model: str
    relationship_type: str  # "one-to-many", "many-to-many", "one-to-one"
    field_name: str
    is_required: bool
    
    def to_dict(self) -> dict:
        return {
            "source_model": self.source_model,
            "target_model": self.target_model,
            "relationship_type": self.relationship_type,
            "field_name": self.field_name,
            "is_required": self.is_required,
        }


@dataclass 
class AppInfo:
    """Information about a Django app."""
    name: str
    models: list[ModelInfo] = field(default_factory=list)
    description: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "models": [m.to_dict() for m in self.models],
            "model_count": len(self.models),
        }


@dataclass
class ProjectAnalysis:
    """Complete analysis of a Django project."""
    apps: list[AppInfo] = field(default_factory=list)
    models: list[ModelInfo] = field(default_factory=list)
    relationships: list[RelationshipInfo] = field(default_factory=list)
    
    # Summary statistics
    total_models: int = 0
    total_fields: int = 0
    total_relationships: int = 0
    
    def to_dict(self) -> dict:
        return {
            "summary": {
                "total_apps": len(self.apps),
                "total_models": self.total_models,
                "total_fields": self.total_fields,
                "total_relationships": self.total_relationships,
            },
            "apps": [app.to_dict() for app in self.apps],
            "models": [m.to_dict() for m in self.models],
            "relationships": [r.to_dict() for r in self.relationships],
        }
    
    def get_model_by_name(self, full_name: str) -> Optional[ModelInfo]:
        """Get a model by its full name (app_label.ModelName)."""
        for model in self.models:
            if model.full_name == full_name:
                return model
        return None
    
    def get_models_for_app(self, app_name: str) -> list[ModelInfo]:
        """Get all models for a specific app."""
        return [m for m in self.models if m.app_label == app_name]
    
    def get_relationships_for_model(self, model_name: str) -> list[RelationshipInfo]:
        """Get all relationships where this model is the source."""
        return [r for r in self.relationships if r.source_model == model_name]
    
    def get_incoming_relationships(self, model_name: str) -> list[RelationshipInfo]:
        """Get all relationships where this model is the target."""
        return [r for r in self.relationships if r.target_model == model_name]


class ProjectAnalyzer:
    """Analyzes a Django project structure and relationships."""
    
    def __init__(self, models: list[ModelInfo]):
        self.models = models
    
    def analyze(self) -> ProjectAnalysis:
        """Perform complete project analysis."""
        analysis = ProjectAnalysis()
        
        # Group models by app
        apps_dict: dict[str, list[ModelInfo]] = {}
        for model in self.models:
            if model.app_label not in apps_dict:
                apps_dict[model.app_label] = []
            apps_dict[model.app_label].append(model)
        
        # Create app info objects
        for app_name, app_models in apps_dict.items():
            app_info = AppInfo(
                name=app_name,
                models=app_models,
            )
            analysis.apps.append(app_info)
        
        # Store all models
        analysis.models = self.models.copy()
        
        # Extract relationships
        analysis.relationships = self._extract_relationships()
        
        # Calculate statistics
        analysis.total_models = len(self.models)
        analysis.total_fields = sum(len(m.fields) for m in self.models)
        analysis.total_relationships = len(analysis.relationships)
        
        return analysis
    
    def _extract_relationships(self) -> list[RelationshipInfo]:
        """Extract all relationships between models."""
        relationships = []
        
        for model in self.models:
            for field in model.fields:
                if field.is_foreign_key:
                    relationships.append(RelationshipInfo(
                        source_model=model.full_name,
                        target_model=field.related_model or "Unknown",
                        relationship_type="many-to-one",
                        field_name=field.name,
                        is_required=not field.null,
                    ))
                elif field.is_many_to_many:
                    relationships.append(RelationshipInfo(
                        source_model=model.full_name,
                        target_model=field.related_model or "Unknown",
                        relationship_type="many-to-many",
                        field_name=field.name,
                        is_required=False,  # M2M is always optional
                    ))
                elif field.is_one_to_one:
                    relationships.append(RelationshipInfo(
                        source_model=model.full_name,
                        target_model=field.related_model or "Unknown",
                        relationship_type="one-to-one",
                        field_name=field.name,
                        is_required=not field.null,
                    ))
        
        return relationships
    
    def get_entity_groups(self) -> dict[str, list[str]]:
        """
        Group related entities together based on relationships.
        Useful for identifying bounded contexts or modules.
        """
        # Build adjacency list
        graph: dict[str, set[str]] = {}
        for model in self.models:
            graph[model.full_name] = set()
        
        for rel in self._extract_relationships():
            if rel.source_model in graph:
                graph[rel.source_model].add(rel.target_model)
            if rel.target_model in graph:
                graph[rel.target_model].add(rel.source_model)
        
        # Find connected components using DFS
        visited = set()
        groups = {}
        
        for model_name in graph:
            if model_name not in visited:
                component = []
                self._dfs(model_name, graph, visited, component)
                # Use the first model's app as group name
                group_name = model_name.split(".")[0]
                if group_name not in groups:
                    groups[group_name] = []
                groups[group_name].extend(component)
        
        return groups
    
    def _dfs(
        self,
        node: str,
        graph: dict[str, set[str]],
        visited: set[str],
        component: list[str],
    ) -> None:
        """Depth-first search for finding connected components."""
        visited.add(node)
        component.append(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                self._dfs(neighbor, graph, visited, component)
    
    def identify_core_entities(self) -> list[str]:
        """
        Identify core/central entities based on relationship count.
        These are typically the most important models in the system.
        """
        # Count incoming and outgoing relationships
        relationship_count: dict[str, int] = {}
        
        for model in self.models:
            relationship_count[model.full_name] = 0
        
        for rel in self._extract_relationships():
            if rel.source_model in relationship_count:
                relationship_count[rel.source_model] += 1
            if rel.target_model in relationship_count:
                relationship_count[rel.target_model] += 1
        
        # Sort by relationship count
        sorted_models = sorted(
            relationship_count.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        
        # Return top models (with at least 1 relationship)
        return [m[0] for m in sorted_models if m[1] > 0][:10]
    
    def detect_patterns(self) -> dict[str, list[str]]:
        """
        Detect common patterns in the models.
        """
        patterns = {
            "audit_models": [],        # Models with created_at, updated_at
            "soft_delete": [],         # Models with is_deleted or deleted_at
            "status_workflow": [],     # Models with status field
            "hierarchical": [],        # Models with self-referential FK
            "polymorphic": [],         # Abstract base models with children
            "junction_tables": [],     # Models that are purely for M2M
        }
        
        for model in self.models:
            field_names = {f.name.lower() for f in model.fields}
            field_types = {f.field_type for f in model.fields}
            
            # Check for audit pattern
            if "created_at" in field_names or "created" in field_names:
                if "updated_at" in field_names or "modified" in field_names:
                    patterns["audit_models"].append(model.full_name)
            
            # Check for soft delete
            if "is_deleted" in field_names or "deleted_at" in field_names:
                patterns["soft_delete"].append(model.full_name)
            
            # Check for status workflow
            if "status" in field_names or "state" in field_names:
                patterns["status_workflow"].append(model.full_name)
            
            # Check for hierarchical (self-referential)
            for f in model.fields:
                if f.is_foreign_key and f.related_model == model.full_name:
                    patterns["hierarchical"].append(model.full_name)
                    break
            
            # Check for abstract base
            if model.is_abstract:
                patterns["polymorphic"].append(model.full_name)
            
            # Check for junction table (mostly FKs/M2Ms)
            relation_fields = sum(
                1 for f in model.fields
                if f.is_foreign_key or f.is_many_to_many
            )
            total_data_fields = sum(
                1 for f in model.fields
                if not f.is_primary_key
            )
            if total_data_fields > 0 and relation_fields / total_data_fields > 0.7:
                patterns["junction_tables"].append(model.full_name)
        
        return patterns


def analyze_project(models: list[ModelInfo]) -> ProjectAnalysis:
    """Analyze a Django project from discovered models."""
    analyzer = ProjectAnalyzer(models)
    return analyzer.analyze()
