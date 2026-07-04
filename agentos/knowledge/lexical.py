from __future__ import annotations

import re

STOPWORDS = frozenset({
    "the", "and", "for", "are", "was", "were", "with", "that", "this",
    "from", "has", "have", "not", "any", "all", "within", "than", "into",
    "per", "our", "your", "its", "their", "will", "shall", "may", "must",
    "such", "which", "when", "who", "whom", "they", "them", "then", "there",
})

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return [token for token in _TOKEN_PATTERN.findall(text.lower())
            if len(token) > 2 and token not in STOPWORDS]
