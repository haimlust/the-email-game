"""Conservative identity resolution for fuzzy authorization references."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Mapping, Protocol, Sequence


class SemanticScorer(Protocol):
    def score(
        self, description: str, candidates: Mapping[str, Sequence[str]]
    ) -> Mapping[str, float]: ...


@dataclass(frozen=True)
class Resolution:
    player: str | None
    confidence: float
    margin: float
    reason: str
    ranked: tuple[tuple[str, float], ...]


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(re.findall(r"[\w]+", text, flags=re.UNICODE))


def _ngrams(text: str, n: int = 3) -> Counter[str]:
    compact = f"  {normalize(text)}  "
    return Counter(compact[i : i + n] for i in range(max(0, len(compact) - n + 1)))


def _cosine(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(value * right.get(key, 0) for key, value in left.items())
    lnorm = math.sqrt(sum(value * value for value in left.values()))
    rnorm = math.sqrt(sum(value * value for value in right.values()))
    return dot / (lnorm * rnorm) if lnorm and rnorm else 0.0


def lexical_similarity(left: str, right: str) -> float:
    left_norm, right_norm = normalize(left), normalize(right)
    if not left_norm or not right_norm:
        return 0.0
    left_tokens, right_tokens = set(left_norm.split()), set(right_norm.split())
    union = left_tokens | right_tokens
    jaccard = len(left_tokens & right_tokens) / len(union) if union else 0.0
    char_cosine = _cosine(_ngrams(left_norm), _ngrams(right_norm))
    sequence = SequenceMatcher(None, left_norm, right_norm).ratio()
    return 0.45 * jaccard + 0.35 * char_cosine + 0.20 * sequence


class HybridIdentityResolver:
    """Resolve explicit names first, then combine lexical and semantic scores."""

    def __init__(
        self,
        semantic_scorer: SemanticScorer | None = None,
        *,
        minimum_confidence: float = 0.62,
        minimum_margin: float = 0.12,
    ) -> None:
        self.semantic_scorer = semantic_scorer
        self.minimum_confidence = minimum_confidence
        self.minimum_margin = minimum_margin

    def resolve(
        self,
        description: str,
        candidates: Mapping[str, Sequence[str]],
        known_agents: Sequence[str],
    ) -> Resolution:
        wanted = normalize(description)
        exact = [name for name in known_agents if normalize(name) == wanted]
        if len(exact) == 1:
            return Resolution(exact[0], 1.0, 1.0, "explicit-name", ((exact[0], 1.0),))

        usable = {name: tuple(messages) for name, messages in candidates.items() if messages}
        if not usable:
            return Resolution(None, 0.0, 0.0, "no-history", ())

        lexical = {
            name: max(lexical_similarity(description, message) for message in messages)
            for name, messages in usable.items()
        }
        semantic: Mapping[str, float] = {}
        if self.semantic_scorer is not None:
            try:
                proposed = self.semantic_scorer.score(description, usable)
                checked: dict[str, float] = {}
                for name in usable:
                    value = proposed[name]
                    if isinstance(value, bool):
                        raise ValueError("boolean is not a score")
                    number = float(value)
                    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
                        raise ValueError("semantic score outside [0, 1]")
                    checked[name] = number
                semantic = checked
            # Model/network failures must degrade to conservative lexical matching,
            # never to accidental authorization.
            except Exception:
                semantic = {}

        scores: dict[str, float] = {}
        for name in usable:
            lex = max(0.0, min(1.0, float(lexical[name])))
            if name in semantic:
                sem = max(0.0, min(1.0, float(semantic[name])))
                scores[name] = 0.25 * lex + 0.75 * sem
            else:
                # Lexical matching alone must be very strong to authorize signing.
                scores[name] = lex

        ranked = tuple(sorted(scores.items(), key=lambda item: (-item[1], item[0])))
        best_name, best_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0
        margin = best_score - second_score
        if best_score < self.minimum_confidence:
            return Resolution(None, best_score, margin, "low-confidence", ranked)
        if margin < self.minimum_margin:
            return Resolution(None, best_score, margin, "ambiguous", ranked)
        return Resolution(best_name, best_score, margin, "fuzzy-match", ranked)
