"""
Executed only at once at the startup of the application to register the prompt to langfuse
"""

import logging
from langfuse import Langfuse
lf = Langfuse()

import os
model = os.environ['AZURE_DEPLOYMENT']

def _ensure_prompt(name: str, prompt:str, model:str, temperature=0.2):
    if lf.get_prompt(name, raise_if_not_true=False):
        return False
    lf.create_prompt(name=name,prompt=prompt, config={"model":model,"temperature":temperature},
                     labels=['production'])
    

def register_prompt_once():
    input_gr_prompt = """ """
    output_gr_prompt = """ """
    optimization_prompt = """"""

    _ensure_prompt(name="input-gaurdrail",prompt=input_gr_prompt)
    _ensure_prompt(name="output-gaurdrail",prompt=output_gr_prompt)
    _ensure_prompt(name="optimization-prompt",prompt=optimization_prompt)