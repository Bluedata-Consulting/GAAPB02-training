"""
this ptyhon module validates the reponse of LLM and provides boolean responses for checks
"""

import re

# checking/ validating format of the response

PATTERN = re.compile(r"^\d .*",re.M)

def validate_reply(text:str)->bool:
    return len(PATTERN.findall(text)) >=5
