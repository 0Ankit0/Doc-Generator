"""
AI Client Module

Provides integration with AI providers (Google Gemini, OpenAI) for generating
documentation from model analysis data.
"""

import json
from abc import ABC, abstractmethod
from typing import Optional

from ..config import Config, get_config


class AIClient(ABC):
    """Abstract base class for AI clients."""
    
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate text from a prompt."""
        pass
    
    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        schema: dict,
        system_prompt: Optional[str] = None,
    ) -> dict:
        """Generate structured JSON response from a prompt."""
        pass


class GeminiClient(AIClient):
    """Google Gemini API client."""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self._model = None
    
    @property
    def model(self):
        """Lazy initialization of Gemini model."""
        if self._model is None:
            import google.generativeai as genai
            
            genai.configure(api_key=self.config.gemini_api_key)
            self._model = genai.GenerativeModel(self.config.ai_model)
        return self._model
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate text using Gemini."""
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        response = self.model.generate_content(full_prompt)
        return response.text
    
    def generate_structured(
        self,
        prompt: str,
        schema: dict,
        system_prompt: Optional[str] = None,
    ) -> dict:
        """Generate structured JSON response using Gemini."""
        json_instruction = (
            f"\n\nRespond with valid JSON matching this schema:\n"
            f"```json\n{json.dumps(schema, indent=2)}\n```\n"
            f"Only output the JSON, no other text."
        )
        
        full_prompt = prompt + json_instruction
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{full_prompt}"
        
        response = self.model.generate_content(full_prompt)
        
        # Parse JSON from response
        text = response.text.strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json) and last line (```)
            text = "\n".join(lines[1:-1])
        
        return json.loads(text)


class OpenAIClient(AIClient):
    """OpenAI API client."""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self._client = None
    
    @property
    def client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.config.openai_api_key)
        return self._client
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate text using OpenAI."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
        )
        return response.choices[0].message.content
    
    def generate_structured(
        self,
        prompt: str,
        schema: dict,
        system_prompt: Optional[str] = None,
    ) -> dict:
        """Generate structured JSON response using OpenAI."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        json_instruction = (
            f"\n\nRespond with valid JSON matching this schema:\n"
            f"```json\n{json.dumps(schema, indent=2)}\n```"
        )
        messages.append({"role": "user", "content": prompt + json_instruction})
        
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            response_format={"type": "json_object"},
        )
        
        return json.loads(response.choices[0].message.content)


def get_ai_client(config: Optional[Config] = None) -> AIClient:
    """Get the appropriate AI client based on configuration."""
    config = config or get_config()
    
    if config.ai_provider == "openai":
        return OpenAIClient(config)
    return GeminiClient(config)


# Prompt templates
SYSTEM_PROMPT = """You are an expert software architect and technical documentation specialist.
You analyze Django/Python code structures and generate clear, accurate technical documentation.
Your outputs should be professional, well-organized, and follow best practices for technical diagrams."""


ER_DIAGRAM_PROMPT = """Analyze the following Django models and generate a Mermaid ER diagram.

## Model Data
{model_data}

## Requirements
1. Create a complete ER diagram showing all entities (models) and their relationships
2. Include primary keys and important fields for each entity
3. Show relationship cardinality (one-to-one, one-to-many, many-to-many)
4. Use proper Mermaid erDiagram syntax
5. Group related entities visually when possible

## Output Format
Return ONLY the Mermaid diagram code, starting with "erDiagram"."""


DFD_PROMPT = """Analyze the following Django project structure and generate a Data Flow Diagram.

## Model Data
{model_data}

## Detected Patterns
{patterns}

## Requirements
1. Identify the main data stores (database tables/models)
2. Identify processes (CRUD operations, business logic)
3. Identify external entities (users, external systems)
4. Show data flows between all components
5. Use Mermaid flowchart syntax

## Output Format
Return ONLY the Mermaid flowchart code, starting with "flowchart TD"."""


FLOWCHART_PROMPT = """Based on the Django models below, generate flowcharts for the major business processes.

## Model Data
{model_data}

## Detected Patterns
{patterns}

## Core Entities (by relationship count)
{core_entities}

## Requirements
1. Identify major business processes based on the models
2. Create a flowchart for each identified process
3. Show decision points and flow between steps
4. Include error handling paths where applicable
5. Use Mermaid flowchart syntax

## Output Format
Return multiple Mermaid flowcharts, each preceded by a ## heading describing the process."""


DOCUMENTATION_PROMPT = """Generate comprehensive technical documentation for this Django project.

## Model Data
{model_data}

## Relationships
{relationships}

## Detected Patterns
{patterns}

## Requirements
1. Provide an executive summary of the system
2. Document each app/module and its purpose
3. Explain the data model and relationships
4. Identify and document key business processes
5. Note any architectural patterns used
6. Provide recommendations for improvements

## Output Format
Return well-structured Markdown documentation."""
