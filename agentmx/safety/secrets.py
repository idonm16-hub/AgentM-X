import re

SECRET_PATTERNS = [
    re.compile(r"(?i)api[_-]?key\s*=\s*([A-Za-z0-9\-\._]+)"),
    re.compile(r"(?i)token\s*=\s*([A-Za-z0-9\-\._]+)"),
]

def mask(text: str) -> str:
    s = text or ""
    for pat in SECRET_PATTERNS:
        s = pat.sub(lambda m: s.replace(m.group(1), "****"), s)
    return s
