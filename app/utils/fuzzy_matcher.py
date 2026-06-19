"""
Centralized fuzzy matching utility.

Used for fund name, plan name, and insurer name resolution.
"""

from __future__ import annotations

import re
from typing import Callable, List, Optional, Tuple, TypeVar

T = TypeVar("T")

# Compound word expansions
_COMPOUND_EXPANSIONS: dict[str, str] = {
    "multicap": "multi cap",
    "midcap": "mid cap",
    "smallcap": "small cap",
    "largecap": "large cap",
    "flexicap": "flexi cap",
    "bluechip": "blue chip",
    "shortterm": "short term",
    "longterm": "long term",
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
    expanded = [_COMPOUND_EXPANSIONS.get(w, w) for w in words]
    return " ".join(expanded)


def _tokenize(text: str, keep_stop_words: bool = False) -> List[str]:
    words = text.split()
    if keep_stop_words:
        return words
    return [w for w in words if w not in _STOP_WORDS]


def _extract_numbers(text: str) -> set[str]:
    return set(re.findall(r"\b\d+\b", text))


def fuzzy_score(query: str, candidate: str) -> float:
    """Score how well candidate matches query (0-100)."""
    if not query or not candidate:
        return 0.0

    q_norm = _normalize(query)
    c_norm = _normalize(candidate)

    if q_norm == c_norm:
        return 100.0

    # Number check
    q_numbers = _extract_numbers(q_norm)
    c_numbers = _extract_numbers(c_norm)
    if q_numbers:
        missing = q_numbers - c_numbers
        if missing:
            return max(0.0, 20.0 - len(missing) * 15.0)

    q_tokens = _tokenize(q_norm)
    c_tokens = _tokenize(c_norm)

    if not q_tokens:
        return 90.0 if q_norm in c_norm else 50.0
    if not c_tokens:
        return 0.0

    # Token overlap
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

    # Order bonus
    order_bonus = 0.0
    if len(matched_candidate_indices) >= 2:
        in_order = all(
            matched_candidate_indices[i] <= matched_candidate_indices[i + 1]
            for i in range(len(matched_candidate_indices) - 1)
        )
        if in_order:
            order_bonus = 10.0

    # Length penalty
    extra_tokens = len(c_tokens) - matched_query_tokens
    length_penalty = min(extra_tokens * 4.0, 30.0)

    # Substring bonus
    substring_bonus = 0.0
    if q_norm in c_norm:
        substring_bonus = 15.0
    elif c_norm in q_norm:
        substring_bonus = 10.0

    # Precision bonus
    precision_bonus = 0.0
    if len(c_tokens) <= len(q_tokens) + 1:
        precision_bonus = 5.0

    base_score = coverage * 70.0
    score = base_score + order_bonus + substring_bonus + precision_bonus - length_penalty

    return max(0.0, min(100.0, score))


def insurer_score(query: str, candidate: str) -> float:
    """Score how well two insurer names match (0-100)."""
    if not query or not candidate:
        return 0.0

    q = query.lower().strip()
    c = candidate.lower().strip()

    if q == c:
        return 100.0
    if q in c or c in q:
        return 96.0

    q_tokens = q.split()
    c_tokens = c.split()

    if not q_tokens or not c_tokens:
        return 0.0

    matched = 0
    for qt in q_tokens:
        for ct in c_tokens:
            if qt == ct:
                matched += 1
                break
            if len(qt) >= 3 and (ct.startswith(qt) or qt.startswith(ct)):
                matched += 1
                break

    if matched == 0:
        return 0.0

    coverage = matched / len(q_tokens)
    length_ratio = len(q_tokens) / max(len(c_tokens), 1)
    return min((coverage * 80.0) + (length_ratio * 20.0), 100.0)


def find_best_match(
    query: str,
    candidates: List[T],
    get_name: Callable[[T], str],
    threshold: float = 60.0,
    insurer_query: Optional[str] = None,
    get_insurer: Optional[Callable[[T], str]] = None,
) -> Optional[Tuple[T, float]]:
    """Find the single best fuzzy match from a list of candidates."""
    if not query or not candidates:
        return None

    best_item: Optional[T] = None
    best_score: float = 0.0

    for item in candidates:
        name = get_name(item)
        if not name:
            continue
        score = fuzzy_score(query, name)

        # Insurer bonus
        if insurer_query and get_insurer:
            ins_c = get_insurer(item) or ""
            if insurer_score(insurer_query, ins_c) >= 75:
                score += 10.0
            elif insurer_query.lower() not in ins_c.lower():
                score -= 5.0

        if score > best_score:
            best_score = score
            best_item = item

    if best_item is not None and best_score >= threshold:
        return (best_item, best_score)
    return None


def find_top_matches(
    query: str,
    candidates: List[T],
    get_name: Callable[[T], str],
    threshold: float = 60.0,
    top_k: int = 5,
    insurer_query: Optional[str] = None,
    get_insurer: Optional[Callable[[T], str]] = None,
) -> List[Tuple[T, float]]:
    """Find top-k fuzzy matches above threshold."""
    if not query or not candidates:
        return []

    scored: List[Tuple[T, float]] = []

    for item in candidates:
        name = get_name(item)
        if not name:
            continue
        score = fuzzy_score(query, name)

        if insurer_query and get_insurer:
            ins_c = get_insurer(item) or ""
            if insurer_score(insurer_query, ins_c) >= 75:
                score += 10.0
            elif insurer_query.lower() not in ins_c.lower():
                score -= 5.0

        if score >= threshold:
            scored.append((item, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]
