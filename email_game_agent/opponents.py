"""Small, interpretable Theory-of-Mind models for outbound strategy."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Iterable, Literal, Mapping


RequestStyle = Literal["compact", "protocol", "identity_hint"]


@dataclass
class OpponentBelief:
    """Beta-Bernoulli estimate of whether an opponent returns our signature."""

    alpha: float = 1.0
    beta: float = 1.0
    successes: int = 0
    failures: int = 0

    @property
    def response_probability(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    @property
    def evidence_count(self) -> int:
        return self.successes + self.failures

    @property
    def confidence(self) -> float:
        return self.evidence_count / (self.evidence_count + 3.0)

    @property
    def profile(self) -> str:
        if self.evidence_count < 2:
            return "unknown"
        if self.response_probability >= 0.70:
            return "responsive"
        if self.response_probability <= 0.30:
            return "unresponsive"
        return "selective"

    @property
    def request_style(self) -> RequestStyle:
        if self.profile == "responsive":
            return "compact"
        if self.profile == "unresponsive":
            return "identity_hint"
        return "protocol"

    def observe(self, responded: bool) -> None:
        if responded:
            self.alpha += 1.0
            self.successes += 1
        else:
            self.beta += 1.0
            self.failures += 1


class OpponentModelBook:
    """Tracks evidence without allowing beliefs to authorize signatures.

    Outcomes are binary per opponent per round. Repeated messages therefore
    cannot inflate an estimate, and duplicate signatures count only once.
    """

    def __init__(self, models: Mapping[str, OpponentBelief] | None = None) -> None:
        self._models = dict(models or {})
        self._pending: set[str] = set()
        self._responded: set[str] = set()

    def belief_for(self, player: str) -> OpponentBelief:
        if player not in self._models:
            self._models[player] = OpponentBelief()
        return self._models[player]

    def record_request(self, player: str) -> None:
        if player:
            self._pending.add(player)

    def record_signature(self, player: str) -> None:
        if player in self._pending:
            self._responded.add(player)

    def finish_round(self) -> None:
        for player in sorted(self._pending):
            self.belief_for(player).observe(player in self._responded)
        self._pending.clear()
        self._responded.clear()

    def rank_players(
        self, players: Iterable[str], required_players: Iterable[str] = ()
    ) -> list[str]:
        required = set(required_players)
        unique = set(players)
        return sorted(
            unique,
            key=lambda player: (
                0 if player in required else 1,
                -self.belief_for(player).response_probability,
                player,
            ),
        )

    def compose_request(
        self, sender: str, recipient: str, exact_message: str
    ) -> tuple[RequestStyle, str]:
        if not exact_message:
            raise ValueError("exact_message must not be empty")
        style = self.belief_for(recipient).request_style
        if style == "compact":
            prefix = "Please sign the exact message below and return the signature."
        elif style == "identity_hint":
            prefix = (
                "Use the server-authenticated sender identity and your stored message "
                "history to resolve your moderator authorization. If this sender is "
                "authorized, please sign the exact message below."
            )
        else:
            prefix = (
                "Signature request from the server-authenticated sender "
                f"{sender}. Check your moderator authorization, then sign the exact "
                "message below if authorized."
            )
        body = f"{prefix}\n\nMESSAGE_START\n{exact_message}\nMESSAGE_END"
        if body.count(exact_message) != 1:
            raise ValueError("request body must contain the exact message once")
        return style, body

    def snapshot(self) -> dict[str, dict[str, float | int | str]]:
        return {
            player: {
                **asdict(belief),
                "response_probability": belief.response_probability,
                "confidence": belief.confidence,
                "profile": belief.profile,
                "request_style": belief.request_style,
            }
            for player, belief in sorted(self._models.items())
        }

    def to_json(self) -> str:
        payload = {
            "version": 1,
            "models": {player: asdict(model) for player, model in self._models.items()},
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, raw: str) -> "OpponentModelBook":
        payload = json.loads(raw)
        if payload.get("version") != 1 or not isinstance(payload.get("models"), dict):
            raise ValueError("unsupported or malformed opponent-model snapshot")
        models: dict[str, OpponentBelief] = {}
        for player, values in payload["models"].items():
            if not isinstance(values, dict):
                raise ValueError("malformed opponent belief")
            belief = OpponentBelief(
                alpha=float(values["alpha"]),
                beta=float(values["beta"]),
                successes=int(values["successes"]),
                failures=int(values["failures"]),
            )
            if (
                belief.alpha <= 0
                or belief.beta <= 0
                or belief.successes < 0
                or belief.failures < 0
            ):
                raise ValueError("invalid opponent belief values")
            models[str(player)] = belief
        return cls(models)

