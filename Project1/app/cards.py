"""
This module has response cards format for telcoGPT.
there are 3 cards defined, 
1. Definition
2. Troubleshotting
3. Design
"""

import re

# basic routing usign regex
_RGX_DEF = re.compile(f"(?i)\b(what is|define|explain)\b")
_RGX_TRB = re.compile(f"(?i)\b(error|alarm|fail|downtime|outage|degrade)\b")

CARD_DEF = """ <<CARD=Definition>>
Return exactly five bullets:

1. Concept <=30 words
2. Technology domain (RAN | OSS/BSS | Device)
3. 3GPP sepc ref
4. Key parameters (<5)
5. Typical Use cases
"""

CARD_TRB = """ <<CARD=Troubleshooting>>
Return exactly five bullets:

1. Root Cause(s)
2. Impact on Network
3. KPIs affected
4. Recommended Fix
5. Fallback
"""

CARD_DES = """ <<CARD=Design>>
Return exactly five bullets:

1. Objective
2. Rquired Inputs
3. Best Practice / Formula
4. Example
5. Standards
"""

def dete_card_type(q:str)->str:
    if _RGX_DEF.search(q): return CARD_DEF
    if _RGX_TRB.search(q): return CARD_TRB
    return CARD_DES
