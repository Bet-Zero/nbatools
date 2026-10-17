"""Frozen P2 experiment: lexical clause normalization before the existing interpreter.

No model, network, generated code, SQL, or answer computation. Unknown wording
is retained for the incumbent's normal qualification/refusal path.
"""

import re

RULES = (
    (r"\bwin[- ]loss\s+(?:mark|record)\b", "record"),
    (r"\bw-l\s+(?:mark|record)\b", "record"),
    (r"\bfacing\b", "against"),
    (r"\bper\s+(?:outing|contest)\b", "per game"),
    (r"\bnot\s+fewer\s+than\b", "at least"),
    (r"\bno\s+more\s+than\b", "at most"),
    (r"\bgreater\s+than\b", "over"),
    (r"\bfewer\s+than\b", "under"),
    (r"\bat\s+their\s+own\s+arena\b", "at home"),
    (r"\bcampaigns\b", "seasons"),
    (r"\bcampaign\b", "season"),
)


def interpret(query):
    for pattern, replacement in RULES:
        query = re.sub(pattern, replacement, query, flags=re.IGNORECASE)
    return query
