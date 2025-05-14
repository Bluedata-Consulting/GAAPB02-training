"""
Executed once at app start‑up to (idempotently) register prompts.
"""

import logging
from langfuse import Langfuse

_LOGGER = logging.getLogger(__name__)
_langfuse = Langfuse()


def _ensure_prompt(name: str, prompt: str, model="gpt-4o", temperature=0.7):
    if _langfuse.get_prompt(name, raise_if_not_found=False):
        _LOGGER.debug("Prompt %s already exists", name)
        return
    _langfuse.create_prompt(
        name=name,
        prompt=prompt,
        config={"model": model, "temperature": temperature},
        labels=["production"],
    )
    _LOGGER.info("Prompt %s created", name)


def register_prompts_once():
    _ensure_prompt(
        "input-guardrail",
        """
        You are a guardrail…
        (same prompt text as before)
        """,
    )
    _ensure_prompt(
        "output-guardrail",
        """
        You are a code quality guardrail…
        (same prompt text as before)
        """,
    )
    _ensure_prompt(
        "optimize-code",
        """
        You are an expert code optimizer…
        (same prompt text as before)
        """,
    )
