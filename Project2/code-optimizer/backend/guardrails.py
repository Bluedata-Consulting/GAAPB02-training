from __future__ import annotations

import logging
from functools import lru_cache
from typing import List

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel, Field
from langfuse import Langfuse
from langfuse.callback import CallbackHandler

from secrets import get_secret, prime_langfuse_env

prime_langfuse_env()
_LOGGER = logging.getLogger(__name__)
_langfuse = Langfuse()


# ───────────────────── Prompt caching helpers ──────────────────────
@lru_cache
def _prompt(name: str):
    return _langfuse.get_prompt(name)


def _llm(model: str, temperature: float):
    return AzureChatOpenAI(
        azure_endpoint="https://user1-mai722r2-eastus2.openai.azure.com/",
        api_key=get_secret("AZURE-OPENAI-API-KEY"),
        api_version="2024-12-01-preview",
        model=model,
        temperature=temperature,
    )


# ───────────────────────── Input guardrail ──────────────────────────
class _InputGuardrailResp(BaseModel):
    code: bool = Field(description="True if code meets conditions, False otherwise")
    condition: str


def input_guardrail(code: str) -> (bool, str):
    p = _prompt("input-guardrail")
    parser = JsonOutputParser(pydantic_object=_InputGuardrailResp)

    chain = (
        PromptTemplate(
            template=p.prompt,
            input_variables=["code"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        | _llm(p.config["model"], float(p.config["temperature"]))
        | parser
    )

    result: _InputGuardrailResp = chain.invoke({"code": code})
    return result.code, result.condition


# ──────────────────────── Output guardrail ──────────────────────────
class _OutputGuardrailResp(BaseModel):
    response: bool


def output_guardrail(optimized_code: str, human_feedback_list: List[str]) -> bool:
    p = _prompt("output-guardrail")
    parser = JsonOutputParser(pydantic_object=_OutputGuardrailResp)

    chain = (
        PromptTemplate(
            template=p.prompt,
            input_variables=["optimized_code", "human_feedback_list"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        | _llm(p.config["model"], float(p.config["temperature"]))
        | parser
    )

    return chain.invoke(
        {"optimized_code": optimized_code, "human_feedback_list": human_feedback_list}
    ).response
