"""Metrics for evaluating fuzzy identity-resolution strategies."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from .resolver import HybridIdentityResolver


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    description: str
    expected_player: str
    candidates: Mapping[str, Sequence[str]]


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    expected_player: str
    selected_player: str | None
    top_player: str | None
    confidence: float
    margin: float
    reason: str


@dataclass(frozen=True)
class BenchmarkReport:
    results: tuple[CaseResult, ...]

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def correct(self) -> int:
        return sum(item.selected_player == item.expected_player for item in self.results)

    @property
    def wrong_authorizations(self) -> int:
        return sum(item.selected_player is not None and item.selected_player != item.expected_player for item in self.results)

    @property
    def abstentions(self) -> int:
        return sum(item.selected_player is None for item in self.results)

    @property
    def top_one_correct(self) -> int:
        return sum(item.top_player == item.expected_player for item in self.results)

    def summary(self) -> dict[str, float | int]:
        denominator = self.total or 1
        return {"cases": self.total, "authorized_correctly": self.correct, "wrong_authorizations": self.wrong_authorizations, "abstentions": self.abstentions, "top_one_correct": self.top_one_correct, "safe_accuracy": self.correct / denominator, "unsafe_rate": self.wrong_authorizations / denominator, "abstention_rate": self.abstentions / denominator, "top_one_accuracy": self.top_one_correct / denominator}


def load_cases(path: str | Path) -> list[BenchmarkCase]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("benchmark file must contain a JSON list")
    cases = []
    for item in raw:
        candidates = item.get("candidates")
        if not isinstance(candidates, dict) or not candidates:
            raise ValueError("each benchmark case needs candidates")
        expected = str(item["expected_player"])
        if expected not in candidates:
            raise ValueError("expected player must be one of the candidates")
        cases.append(BenchmarkCase(str(item["case_id"]), str(item["description"]), expected, {str(name): tuple(map(str, messages)) for name, messages in candidates.items()}))
    return cases


def evaluate_cases(cases: Iterable[BenchmarkCase], resolver: HybridIdentityResolver) -> BenchmarkReport:
    results = []
    for case in cases:
        resolution = resolver.resolve(case.description, case.candidates, tuple(case.candidates))
        top_player = resolution.ranked[0][0] if resolution.ranked else None
        results.append(CaseResult(case.case_id, case.expected_player, resolution.player, top_player, resolution.confidence, resolution.margin, resolution.reason))
    return BenchmarkReport(tuple(results))

