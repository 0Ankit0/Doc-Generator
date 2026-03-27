"""AI provider clients and prompts."""

from __future__ import annotations

from abc import ABC, abstractmethod
import json

from ..config import Config


class AIClient(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        raise NotImplementedError


class GeminiClient(AIClient):
    def __init__(self, config: Config):
        self.config = config
        self._model = None

    @property
    def model(self):
        if self._model is None:
            import google.generativeai as genai
            genai.configure(api_key=self.config.gemini_api_key)
            self._model = genai.GenerativeModel(self.config.ai_model)
        return self._model

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        return self.model.generate_content(full_prompt).text


class OpenAIClient(AIClient):
    def __init__(self, config: Config):
        self.config = config
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.config.openai_api_key)
        return self._client

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )
        return response.choices[0].message.content or ""


def get_ai_client(config: Config) -> AIClient:
    return OpenAIClient(config) if config.ai_provider == "openai" else GeminiClient(config)


SYSTEM_PROMPT = """You are a principal software architect.
Given a repository structure and high-level source symbols, generate practical system documentation.
Always produce concrete, implementation-oriented outputs with Mermaid where diagrams are requested."""


def build_prompt(doc_type: str, structure: dict, analysis: dict, requirements: str) -> str:
    instructions = {
        "overview": "Write a concise system overview and module map in Markdown.",
        "architecture": "Generate an architecture design doc with sections, boundaries, data stores, and deployment notes.",
        "dfd": "Generate a Mermaid flowchart TD data-flow diagram with entities, processes, and data stores.",
        "sequence": "Generate a Mermaid sequenceDiagram for the main request lifecycle and an async/background flow.",
        "flowchart": "Generate a Mermaid flowchart for major business flow, including decision nodes and error paths.",
        "requirements": "Generate a requirements/spec document listing assumptions, functional and non-functional requirements, and constraints.",
        "components": "Generate a component design document with component responsibilities, interfaces, dependencies, and ownership.",
        "deployment": "Generate a deployment and operations doc covering environments, runtime topology, CI/CD, observability, and rollback strategy.",
    }

    return "\n".join([
        f"Document type: {doc_type}",
        instructions.get(doc_type, "Generate useful technical documentation."),
        "",
        "Project structure and symbols:",
        json.dumps(structure, indent=2),
        "",
        "Derived analysis:",
        json.dumps(analysis, indent=2),
        "",
        f"User requirements: {requirements or 'None provided.'}",
        "",
        "Output only the requested document content.",
    ])
