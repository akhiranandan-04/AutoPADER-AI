"""Runtime configuration loaded from environment variables.

Configuration values are read from the process environment and an optional
``.env`` file via ``python-dotenv``. Keeping settings here (and out of
business modules) lets the rest of the pipeline stay environment-agnostic.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openrouter/free"
DEFAULT_TIMEOUT_S = 120.0
DEFAULT_THINKING = "disabled"
DEFAULT_PROMPTS_DIR = "autopader/prompts"


@dataclass(frozen=True)
class Settings:
    """Resolved runtime settings."""

    openrouter_api_key: str = ""
    openrouter_base_url: str = DEFAULT_BASE_URL
    openrouter_model: str = DEFAULT_MODEL
    openrouter_timeout_s: float = DEFAULT_TIMEOUT_S
    openrouter_thinking: str = DEFAULT_THINKING
    prompts_dir: str = DEFAULT_PROMPTS_DIR

    @property
    def has_api_key(self) -> bool:
        """Whether an OpenRouter API key is available for live generation."""
        return bool(self.openrouter_api_key)


def load_settings(env_file: str | os.PathLike[str] | None = None) -> Settings:
    """Load settings from the environment, optionally via an explicit .env file."""
    load_dotenv(env_file)
    return Settings(
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        openrouter_base_url=os.getenv("OPENROUTER_BASE_URL", DEFAULT_BASE_URL),
        openrouter_model=os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL),
        openrouter_timeout_s=float(os.getenv("OPENROUTER_TIMEOUT_S", str(DEFAULT_TIMEOUT_S))),
        openrouter_thinking=os.getenv("OPENROUTER_THINKING", DEFAULT_THINKING),
        prompts_dir=os.getenv("PROMPTS_DIR", DEFAULT_PROMPTS_DIR),
    )
