from __future__ import annotations

import re

STOPWORDS = frozenset({
    "the", "and", "for", "are", "was", "were", "with", "that", "this",
    "from", "has", "have", "not", "any", "all", "within", "than", "into",
    "per", "our", "your", "its", "their", "will", "shall", "may", "must",
    "such", "which", "when", "who", "whom", "they", "them", "then", "there",
})

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


NEGATION_CUES = frozenset({
    "not", "never", "without", "cannot", "prohibited", "forbidden",
    "excluded", "denied", "refuse", "refused", "fails", "noncompliant",
})


def tokenize(text: str) -> list[str]:
    return [token for token in _TOKEN_PATTERN.findall(text.lower())
            if len(token) > 2 and token not in STOPWORDS]


def has_negation(text: str) -> bool:
    return bool(set(_TOKEN_PATTERN.findall(text.lower())) & NEGATION_CUES)
