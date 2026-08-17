"""LLM integration: clients, prompt rendering, generation and grounding."""

from .client import DeepSeekClient, EchoClient, LLMClient, build_client
from .generator import GeneratedSection, generate_section
from .grounding import grounding_check
from .prompts import prompt_version, render_prompt, render_template

__all__ = [
    "DeepSeekClient",
    "EchoClient",
    "LLMClient",
    "build_client",
    "GeneratedSection",
    "generate_section",
    "grounding_check",
    "render_prompt",
    "render_template",
    "prompt_version",
]
