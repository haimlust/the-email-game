"""Minimal trusted memory used for cross-round identity resolution."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class MessageObservation:
    round_id: str
    player: str
    exact_message: str


class AgentMemory:
    def __init__(self) -> None:
        self._observations: list[MessageObservation] = []
        self._seen: set[tuple[str, str, str]] = set()

    def observe_request(self, round_id: str, player: str, exact_message: str) -> None:
        """Record only the structured message field supplied by the adapter."""
        if not player or not exact_message:
            return
        key = (round_id, player, exact_message)
        if key in self._seen:
            return
        self._seen.add(key)
        self._observations.append(MessageObservation(*key))

    def histories(self, *, before_round: str | None = None) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        for item in self._observations:
            if before_round is not None and item.round_id == before_round:
                continue
            result.setdefault(item.player, []).append(item.exact_message)
        return result

    def to_json(self) -> str:
        return json.dumps(
            {"version": 1, "observations": [asdict(item) for item in self._observations]},
            ensure_ascii=False,
            separators=(",", ":"),
        )

    @classmethod
    def from_json(cls, raw: str) -> "AgentMemory":
        data = json.loads(raw)
        if data.get("version") != 1 or not isinstance(data.get("observations"), list):
            raise ValueError("unsupported or malformed memory snapshot")
        memory = cls()
        for item in data["observations"]:
            memory.observe_request(
                str(item["round_id"]), str(item["player"]), str(item["exact_message"])
            )
        return memory

