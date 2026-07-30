"""Run with: python benchmarks/run_resolver_benchmark.py"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from email_game_agent.benchmark import evaluate_cases, load_cases
from email_game_agent.resolver import HybridIdentityResolver


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark fuzzy identity resolution")
    parser.add_argument("--cases", type=Path, default=Path(__file__).with_name("resolver_cases.json"))
    parser.add_argument("--confidence", type=float, default=0.62)
    parser.add_argument("--margin", type=float, default=0.12)
    args = parser.parse_args()
    resolver = HybridIdentityResolver(minimum_confidence=args.confidence, minimum_margin=args.margin)
    report = evaluate_cases(load_cases(args.cases), resolver)
    print(json.dumps(report.summary(), indent=2, sort_keys=True))
    print("\nCases not authorized correctly:")
    for result in report.results:
        if result.selected_player != result.expected_player:
            print(f"- {result.case_id}: expected={result.expected_player} selected={result.selected_player} top={result.top_player} confidence={result.confidence:.3f} margin={result.margin:.3f} reason={result.reason}")
    return 1 if report.wrong_authorizations else 0


if __name__ == "__main__":
    raise SystemExit(main())

