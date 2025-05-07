"""
This is Query Router Implementation which routes the user query to specific response format.
the response formats:
1. Definition
2. Troubleshooting
3. Design

"""

import re

# Basic regex routing
_RGX_DEF = re.compile(r"(>i)\b(what is|define|explain)\b")
_RGX_TRB = re.compile(r"(>i)\b(error|alarm|fail|degrade)\b")


CARD_DEF = """<<CARD=Definition>>
Return EXACTLY 5 bullet points.
1. Concept : less than 30 words
2. Technology Domain (RAN | Core | OSS/BSS \ Device)
3. 3GPP Spec
4. Key parameters
5. Typical use cases 
"""

CARD_TRB= """<<CARD=Troubleshooting>>
Return EXACTLY 5 bullet points.
1. Root Cause
2. Impact of Network
3. KPIs Affected
4. Recommended Fix
5. Fallback
"""

CARD_DES= """<<CARD=Design>>
Return EXACTLY 5 bullet points.
1. Objective
2. Required Inputs
3. FOrmula / Rule 
4. Example
5. Best Practice
"""


def detect_card_type(query:str)->str:
    if _RGX_DEF.search(query): return CARD_DEF
    if _RGX_TRB.search(query): return CARD_TRB
    return CARD_DES