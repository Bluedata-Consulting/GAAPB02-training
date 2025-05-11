import re, html
from typing import Final

_tag_PATTERN = re.compile(r"<[^>]+>", re.M)
_bullet_PATTERN = re.compile("^(?:\\d+\\.|[-*])\\s", re.M)
def validate_reply(text:str)->bool:
    plain = _tag_PATTERN.sub("",html.unescape(text))
    return len(_bullet_PATTERN.findall(plain))>=5