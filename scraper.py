"""
TenantCaseLawScraper — scraper.py
California tenant-rights case law scraper.
CourtListener-first, SQLite-backed, with topic tagging, outcome detection,
and domain-tuned relevance scoring for unpermitted-unit / RSO /
landlord-harassment research.
"""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

QUERY_STOPWORDS: frozenset[str] = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "of",
        "in",
        "on",
        "at",
        "to",
        "for",
        "is",
        "was",
        "are",
        "were",
        "be",
        "been",
        "being",
        "that",
        "this",
        "it",
        "its",
        "with",
        "by",
        "from",
        "as",
        "have",
        "had",
        "has",
        "not",
        "but",
        "all",
        "which",
        "who",
        "what",
        "where",
        "when",
        "how",
        "case",
        "court",
        "v",
        "vs",
        "california",
        "ca",
        "city",
        "county",
        "tenant",
        "landlord",
        "plaintiff",
        "defendant",
        "motion",
        "order",
        "judgment",
        "appeal",
        "action",
    }
)

# Legal acronyms that must be preserved regardless of length
ACRONYM_WHITELIST: frozenset[str] = frozenset(
    {"rso", "taho", "feha", "ada", "omi", "ud", "ab", "sb"}
)


def _extract_query_terms(query: str) -> list[str]:
    """Return meaningful search tokens from *query*.

    Rules
    -----
    - Lowercases the input.
    - Splits on whitespace / punctuation.
    - Strips tokens that appear in QUERY_STOPWORDS.
    - Keeps tokens in ACRONYM_WHITELIST even if they are shorter than 4 chars.
    - Drops tokens whose length is < 4 and that are NOT in ACRONYM_WHITELIST.
    - Returns an empty list when every token is a stopword or too short.
    """
    tokens = re.split(r"[\s\W]+", query.lower())
    result: list[str] = []
    for tok in tokens:
        if not tok:
            continue
        if tok in QUERY_STOPWORDS:
            continue
        if tok in ACRONYM_WHITELIST:
            result.append(tok)
            continue
        if len(tok) < 4:
            continue
        result.append(tok)
    return result


def query_matches(text: str, query: str) -> bool:
    """Return True when *text* satisfies *query*.

    - Extracts terms via :func:`_extract_query_terms`.
    - Empty term list (all-stopword / empty query) → browse mode → True.
    - All extracted terms must appear in the lowercased *text* (AND semantics).
    - Case-insensitive.
    """
    terms = _extract_query_terms(query)
    if not terms:
        return True
    low = text.lower()
    return all(term in low for term in terms)


# ---------------------------------------------------------------------------
# Topic classification
# ---------------------------------------------------------------------------

# Each entry is (topic_tag, [keyword_patterns …])
# Patterns are matched case-insensitively anywhere in the text.
_TOPIC_PATTERNS: list[tuple[str, list[str]]] = [
    (
        "unpermitted_unit",
        [
            r"unpermitted\s+unit",
            r"illegal\s+unit",
            r"illegal\s+dwelling",
            r"unpermitted\s+dwelling",
            r"non-?permitted\s+unit",
            r"unpermitted\s+addition",
        ],
    ),
    (
        "rent_disgorgement",
        [
            r"rent\s+disgorgement",
            r"disgorgement\s+of\s+rent",
            r"restitution\s+of\s+rent",
            r"refund\s+of\s+rent",
            r"return\s+of\s+rent",
        ],
    ),
    (
        "rso_coverage",
        [
            r"\brso\b",
            r"rent\s+stabilization\s+ordinance",
            r"los\s+angeles\s+municipal\s+code.*151",
            r"lamc.*151",
            r"rent\s+control\s+ordinance",
        ],
    ),
    (
        "certificate_of_occupancy",
        [
            r"certificate\s+of\s+occupancy",
            r"certificate\s+of\s+use",
            r"occupancy\s+permit",
            r"building\s+permit.*occupanc",
            r"no\s+certificate\s+of\s+occupanc",
        ],
    ),
    (
        "landlord_harassment",
        [
            r"landlord\s+harassment",
            r"retaliator[y]?\s+eviction",
            r"retaliati",
            r"intimidat",
            r"harassment\s+by\s+landlord",
            r"civil\s+harassment",
        ],
    ),
    (
        "wrongful_eviction",
        [
            r"wrongful\s+eviction",
            r"unlawful\s+eviction",
            r"constructive\s+eviction",
            r"illegal\s+eviction",
        ],
    ),
    (
        "habitability",
        [
            r"implied\s+warranty\s+of\s+habitability",
            r"uninhabitable",
            r"substandard\s+(housing|condition)",
            r"breach\s+of\s+habitability",
            r"habitabilit",
        ],
    ),
    (
        "illegal_subtenancy",
        [
            r"illegal\s+subten",
            r"unauthorized\s+subten",
            r"subleas",
            r"illegal\s+subleas",
        ],
    ),
    (
        "taho_coverage",
        [
            r"\btaho\b",
            r"tenant\s+anti-harassment\s+ordinance",
            r"tenant\s+anti\s+harassment",
        ],
    ),
    (
        "feha_coverage",
        [
            r"\bfeha\b",
            r"fair\s+employment\s+and\s+housing\s+act",
        ],
    ),
    (
        "owner_move_in",
        [
            r"\bomi\b",
            r"owner[\s-]?move[\s-]?in",
            r"owner\s+occupancy\s+eviction",
        ],
    ),
]


def classify_topics(text: str) -> list[str]:
    """Return a list of topic tags that apply to *text*.

    Matching is case-insensitive.  An empty *text* returns ``[]``.
    """
    if not text:
        return []
    topics: list[str] = []
    low = text.lower()
    for tag, patterns in _TOPIC_PATTERNS:
        for pat in patterns:
            if re.search(pat, low):
                topics.append(tag)
                break
    return topics


# ---------------------------------------------------------------------------
# Outcome detection
# ---------------------------------------------------------------------------

_OUTCOME_PATTERNS: dict[str, list[str]] = {
    "tenant_won": [
        r"judgment\s+(in\s+favor\s+of|for)\s+(the\s+)?plaintiff",
        r"tenant\s+prevail",
        r"verdict\s+for\s+(the\s+)?plaintiff",
        r"summary\s+judgment\s+denied",
        r"injunction\b.{0,30}\bgranted",
        r"affirmed\s+.*\s+tenant",
        r"reversed\s+.*\s+landlord",
        r"tenant\s+awarded",
        r"damages\s+awarded\s+to\s+tenant",
        r"award(?:ed)?\s+to\s+(?:the\s+)?tenant",
    ],
    "landlord_won": [
        r"judgment\s+(in\s+favor\s+of|for)\s+(the\s+)?defendant",
        r"landlord\s+prevail",
        r"verdict\s+for\s+(the\s+)?defendant",
        r"summary\s+judgment\s+granted",
        r"unlawful\s+detainer\b.{0,30}\bgranted",
        r"writ\s+of\s+possession\s+issued",
        r"affirmed\s+.*\s+landlord",
        r"reversed\s+.*\s+tenant",
        r"demurrer\s+sustained",
        r"award(?:ed)?\s+to\s+(?:the\s+)?landlord",
    ],
    "dismissed": [
        r"case\s+dismissed",
        r"complaint\s+dismissed",
        r"action\s+dismissed",
        r"dismissed\s+with\s+prejudice",
        r"dismissed\s+without\s+prejudice",
        r"order\s+of\s+dismissal",
        r"voluntarily\s+dismissed",
    ],
    "settled": [
        r"settle[d]?",
        r"settlement\s+agreement",
        r"stipulat",
        r"consent\s+judgment",
        r"agreed\s+judgment",
    ],
}


def detect_outcome(text: str) -> str:
    """Detect the litigation outcome described in *text*.

    Returns one of ``"tenant_won"``, ``"landlord_won"``, ``"dismissed"``,
    ``"settled"``, or ``"unknown"``.
    """
    if not text:
        return "unknown"
    low = text.lower()
    for outcome, patterns in _OUTCOME_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, low):
                return outcome
    return "unknown"


# ---------------------------------------------------------------------------
# Relevance scoring
# ---------------------------------------------------------------------------

_STRONG_TOPICS: frozenset[str] = frozenset(
    {
        "unpermitted_unit",
        "rent_disgorgement",
        "rso_coverage",
        "certificate_of_occupancy",
    }
)

_MEDIUM_TOPICS: frozenset[str] = frozenset(
    {
        "landlord_harassment",
        "wrongful_eviction",
        "habitability",
        "illegal_subtenancy",
        "taho_coverage",
        "feha_coverage",
        "owner_move_in",
    }
)

_STRONG_WEIGHT = 0.22
_MEDIUM_WEIGHT = 0.11
_WEAK_WEIGHT = 0.04

_CARTER_COMBO = frozenset({"unpermitted_unit", "rent_disgorgement"})
_SALAZAR_COMBO = frozenset({"rso_coverage", "unpermitted_unit"})

_CARTER_BONUS = 0.18
_SALAZAR_BONUS = 0.12

_STUB_THRESHOLD = 500  # chars


def score_relevance(text: str, query: str, topics: list[str]) -> float:
    """Return a relevance score in *[0.0, 1.0]* for *text*.

    Scoring components
    ------------------
    - Strong topic match  → +0.22 per topic
    - Medium topic match  → +0.11 per topic
    - Weak   topic match  → +0.04 per topic
    - Carter v. Cohen combo (unpermitted_unit + rent_disgorgement) → +0.18
    - Salazar combo       (rso_coverage + unpermitted_unit)        → +0.12
    - Stub penalty: len(text) < 500 → score × 0.5
    - Final score clamped to [0.0, 1.0].
    """
    topic_set = set(topics)
    score = 0.0

    for topic in topic_set:
        if topic in _STRONG_TOPICS:
            score += _STRONG_WEIGHT
        elif topic in _MEDIUM_TOPICS:
            score += _MEDIUM_WEIGHT
        else:
            score += _WEAK_WEIGHT

    # Combination bonuses
    if _CARTER_COMBO.issubset(topic_set):
        score += _CARTER_BONUS
    if _SALAZAR_COMBO.issubset(topic_set):
        score += _SALAZAR_BONUS

    # Stub penalty
    if len(text) < _STUB_THRESHOLD:
        score *= 0.5

    return max(0.0, min(1.0, score))


# ---------------------------------------------------------------------------
# CourtListener source adapter (structural skeleton — pure helpers only)
# ---------------------------------------------------------------------------

_SKIP_OPINION_TYPES: frozenset[str] = frozenset(
    {"030concurrence", "035concurrenceinpart", "040dissent"}
)

_OPINION_PRIORITY: list[str] = ["020lead", "015unanimous", "010combined"]


class CourtListenerSource:
    """Minimal structural skeleton for the CourtListener adapter.

    Only the pure helper methods are implemented here; the network-layer
    ``search()`` method is intentionally omitted so tests remain offline.
    """

    @staticmethod
    def _select_lead_opinion_id(opinions: list[dict[str, Any]]) -> Any:
        """Return the id of the best "lead" opinion from *opinions*.

        Selection rules (in priority order)
        ------------------------------------
        1. Walk ``_OPINION_PRIORITY`` types (020lead → 015unanimous →
           010combined).  Return the first opinion whose ``type`` matches.
        2. Fall back to the first opinion whose ``type`` is NOT in
           ``_SKIP_OPINION_TYPES``.
        3. Last resort (all opinions are concurrences/dissents): return
           ``opinions[0]["id"]`` so we never return ``None`` for a non-empty
           list.

        Parameters
        ----------
        opinions:
            List of opinion dicts.  Each dict must contain at least an ``"id"``
            key and a ``"type"`` key (e.g. ``"020lead"``).

        Returns
        -------
        The ``"id"`` value of the selected opinion, or ``None`` if *opinions*
        is empty.
        """
        if not opinions:
            return None

        # Build a mapping from type → first opinion of that type
        by_type: dict[str, dict[str, Any]] = {}
        for op in opinions:
            op_type = op.get("type", "")
            if op_type not in by_type:
                by_type[op_type] = op

        # Step 1 — walk priority list
        for priority_type in _OPINION_PRIORITY:
            if priority_type in by_type:
                return by_type[priority_type]["id"]

        # Step 2 — first non-skipped opinion
        for op in opinions:
            if op.get("type", "") not in _SKIP_OPINION_TYPES:
                return op["id"]

        # Step 3 — last resort
        return opinions[0]["id"]
