"""
Centralized fuzzy matching utility — v2 (rewritten).

Single source of truth for name-matching logic used across:
- NFO name resolution (nfo_service)
- Plan name resolution (plan_service)
- Insurer name resolution (nfo_service)
- Fund search (fund_service)
- Plan search (plan_service)
"""

from __future__ import annotations

import re
from typing import Callable, List, Optional, Tuple, TypeVar

T = TypeVar("T")

_COMPOUND_EXPANSIONS: dict[str, str] = {
    "multicap": "multi cap",
    "midcap": "mid cap",
    "smallcap": "small cap",
    "largecap": "large cap",
    "flexicap": "flexi cap",
    "bluechip": "blue chip",
    "microfinance": "micro finance",
    "lifecycle": "life cycle",
    "shortterm": "short term",
    "longterm": "long term",
    "ultashort": "ultra short",
    "ultrashort": "ultra short",
}

_STOP_WORDS: set[str] = {
    "fund", "funds", "plan", "plans", "scheme", "option",
    "regular", "direct", "div", "dividend", "the", "of", "and", "in",
    "for", "with", "a", "an", "life", "insurance",
}


def _normalize(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    words = s.split()
    expanded = []
    for w in words:
        if w in _COMPOUND_EXPANSIONS:
            expanded.append(_COMPOUND_EXPANSIONS[w])
        else:
            expanded.append(w)
    return " ".join(expanded)


def _tokenize(text: str, keep_stop_words: bool = False) -> List[str]:
    words = text.split()
    if keep_stop_words:
        return words
    return [w for w in words if w not in _STOP_WORDS]


def _extract_numbers(text: str) -> set[str]:
    return set(re.findall(r"\b\d+\b", text))


def fuzzy_score(query: str, candidate: str) -> float:
    if not query or not candidate:
        return 0.0

    q_norm = _normalize(query)
    c_norm = _normalize(candidate)

    if q_norm == c_norm:
        return 100.0

    q_numbers = _extract_numbers(q_norm)
    c_numbers = _extract_numbers(c_norm)
    if q_numbers:
        missing = q_numbers - c_numbers
        if missing:
            return max(0.0, 20.0 - len(missing) * 15.0)

    q_tokens = _tokenize(q_norm)
    c_tokens = _tokenize(c_norm)

    if not q_tokens:
        if q_norm in c_norm:
            return 90.0
        return 50.0

    if not c_tokens:
        return 0.0

    matched_query_tokens = 0
    matched_candidate_indices: list[int] = []

    for qt in q_tokens:
        best_idx = -1
        for i, ct in enumerate(c_tokens):
            if qt == ct:
                best_idx = i
                break
            if len(qt) >= 3 and (ct.startswith(qt) or qt.startswith(ct)):
                best_idx = i
                break
        if best_idx >= 0:
            matched_query_tokens += 1
            matched_candidate_indices.append(best_idx)

    if matched_query_tokens == 0:
        return 0.0

    coverage = matched_query_tokens / len(q_tokens)

    order_bonus = 0.0
    if len(matched_candidate_indices) >= 2:
        in_order = all(
            matched_candidate_indices[i] <= matched_candidate_indices[i + 1]
            for i in range(len(matched_candidate_indices) - 1)
        )
        if in_order:
            order_bonus = 10.0

    extra_tokens = len(c_tokens) - matched_query_tokens
    length_penalty = min(extra_tokens * 4.0, 30.0)

    substring_bonus = 0.0
    if q_norm in c_norm:
        substring_bonus = 15.0
    elif c_norm in q_norm:
        substring_bonus = 10.0

    precision_bonus = 0.0
    if len(c_tokens) <= len(q_tokens) + 1:
        precision_bonus = 5.0

    base_score = coverage * 70.0
    score = base_score + order_bonus + substring_bonus + precision_bonus - length_penalty

    return max(0.0, min(100.0, score))


def fuzzy_score_with_insurer_bonus(
    query: str,
    candidate: str,
    insurer_query: Optional[str] = None,
    insurer_candidate: Optional[str] = None,
    insurer_bonus: float = 10.0,
) -> float:
    base = fuzzy_score(query, candidate)

    if insurer_query and insurer_candidate:
        ins_q = insurer_query.strip().lower()
        ins_c = insurer_candidate.strip().lower()
        if not ins_q or not ins_c:
            return base
        if ins_q in ins_c or ins_c in ins_q:
            base += insurer_bonus
        else:
            ins_q_tokens = set(ins_q.split())
            ins_c_tokens = set(ins_c.split())
            overlap = ins_q_tokens & ins_c_tokens
            if overlap and len(overlap) >= 1:
                base += insurer_bonus * 0.7
            else:
                base -= insurer_bonus * 0.5

    return base


def find_best_match(
    query: str,
    candidates: List[T],
    get_name: Callable[[T], str],
    threshold: float = 60.0,
    insurer_query: Optional[str] = None,
    get_insurer: Optional[Callable[[T], str]] = None,
) -> Optional[Tuple[T, float]]:
    if not query or not query.strip() or not candidates:
        return None

    best_item: Optional[T] = None
    best_score: float = 0.0

    for item in candidates:
        name = get_name(item)
        if not name:
            continue

        ins_candidate = get_insurer(item) if get_insurer else None
        score = fuzzy_score_with_insurer_bonus(
            query, name,
            insurer_query=insurer_query,
            insurer_candidate=ins_candidate,
        )

        if score > best_score:
            best_score = score
            best_item = item

    if best_item is not None and best_score >= threshold:
        return (best_item, best_score)
    return None
