"""Deterministic event-driven simulator for strategy experiments."""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, field
from typing import Callable, Mapping

from .core import EmailGameCore
from .models import Action, InboundEvent, RequestSignature, RoundAssignment, SignMessage, SubmitSignature


@dataclass(frozen=True)
class PlayerRound:
    """Moderator truth and the view delivered to one player."""

    exact_message: str
    collect_from: tuple[str, ...]
    authorized_refs: tuple[str, ...]
    authorized_players: frozenset[str]


@dataclass(frozen=True)
class InjectedRequest:
    target: str
    sender: str
    requested_message: str
    body: str = ""


@dataclass(frozen=True)
class RoundScenario:
    round_id: str
    players: Mapping[str, PlayerRound]
    injected_requests: tuple[InjectedRequest, ...] = ()


@dataclass
class PlayerMetrics:
    score: int = 0
    requests_sent: int = 0
    requests_received: int = 0
    requests_refused: int = 0
    signatures_provided: int = 0
    signatures_submitted: int = 0
    unauthorized_signatures: int = 0
    unresolved_authorizations: int = 0


@dataclass
class RoundReport:
    round_id: str
    players: dict[str, PlayerMetrics] = field(default_factory=dict)

    @property
    def total_score(self) -> int:
        return sum(item.score for item in self.players.values())

    @property
    def total_unauthorized_signatures(self) -> int:
        return sum(item.unauthorized_signatures for item in self.players.values())

    def as_dict(self) -> dict[str, object]:
        return {
            "round_id": self.round_id,
            "total_score": self.total_score,
            "total_unauthorized_signatures": self.total_unauthorized_signatures,
            "players": {name: asdict(item) for name, item in self.players.items()},
        }

    def format_table(self) -> str:
        headers = ("player", "score", "asked", "signed", "submitted", "bad", "refused")
        rows = [headers]
        for name, item in sorted(self.players.items()):
            rows.append((name, str(item.score), str(item.requests_sent), str(item.signatures_provided), str(item.signatures_submitted), str(item.unauthorized_signatures), str(item.requests_refused)))
        widths = [max(len(row[index]) for row in rows) for index in range(len(headers))]
        rendered = []
        for row_index, row in enumerate(rows):
            rendered.append("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)))
            if row_index == 0:
                rendered.append("  ".join("-" * width for width in widths))
        return "\n".join(rendered)


RequestBodyBuilder = Callable[[str, str, str], str]


def default_request_body(sender: str, recipient: str, exact_message: str) -> str:
    del sender, recipient
    return "Please sign the exact message below.\n\nMESSAGE:\n" + exact_message


class MatchSimulator:
    """Execute core actions until the round's event queue becomes empty."""

    def __init__(self, cores: Mapping[str, EmailGameCore], *, request_body_builder: RequestBodyBuilder = default_request_body) -> None:
        self.cores = dict(cores)
        self.request_body_builder = request_body_builder

    def run_round(self, scenario: RoundScenario) -> RoundReport:
        names = tuple(sorted(scenario.players))
        if set(names) != set(self.cores):
            raise ValueError("scenario players must exactly match simulator cores")
        self._validate_scenario(scenario, names)
        report = RoundReport(scenario.round_id, {name: PlayerMetrics() for name in names})
        queue: deque[tuple[str, Action]] = deque()

        for name in names:
            spec = scenario.players[name]
            assignment = RoundAssignment(scenario.round_id, spec.exact_message, spec.collect_from, spec.authorized_refs, names)
            for action in self.cores[name].start_round(assignment):
                queue.append((name, action))
            report.players[name].unresolved_authorizations = len(self.cores[name].unresolved_authorizations)

        for injected in scenario.injected_requests:
            if injected.target not in self.cores:
                raise ValueError(f"unknown injected-request target: {injected.target}")
            report.players[injected.target].requests_received += 1
            responses = self.cores[injected.target].on_message_batch([InboundEvent(sender=injected.sender, kind="signature_request", body=injected.body, requested_message=injected.requested_message)])
            if not any(isinstance(action, SignMessage) for action in responses):
                report.players[injected.target].requests_refused += 1
            for action in responses:
                queue.append((injected.target, action))

        while queue:
            actor, action = queue.popleft()
            if isinstance(action, RequestSignature):
                self._deliver_request(actor, action, report, queue)
            elif isinstance(action, SignMessage):
                self._deliver_signature(actor, action, scenario, report, queue)
            elif isinstance(action, SubmitSignature):
                self._score_submission(actor, action, scenario, report)
            else:
                raise TypeError(f"unsupported action: {type(action).__name__}")
        for core in self.cores.values():
            core.finish_round()
        return report

    def _deliver_request(self, actor: str, action: RequestSignature, report: RoundReport, queue: deque[tuple[str, Action]]) -> None:
        if action.recipient not in self.cores:
            return
        report.players[actor].requests_sent += 1
        report.players[action.recipient].requests_received += 1
        body = action.body or self.request_body_builder(actor, action.recipient, action.exact_message)
        responses = self.cores[action.recipient].on_message_batch([InboundEvent(sender=actor, kind="signature_request", body=body, requested_message=action.exact_message)])
        if not any(isinstance(response, SignMessage) for response in responses):
            report.players[action.recipient].requests_refused += 1
        for response in responses:
            queue.append((action.recipient, response))

    def _deliver_signature(self, signer: str, action: SignMessage, scenario: RoundScenario, report: RoundReport, queue: deque[tuple[str, Action]]) -> None:
        recipient = action.recipient
        if recipient not in self.cores:
            return
        metrics = report.players[signer]
        metrics.signatures_provided += 1
        if recipient in scenario.players[signer].authorized_players:
            metrics.score += 1
        else:
            metrics.score -= 1
            metrics.unauthorized_signatures += 1
        payload = {"round_id": scenario.round_id, "signer": signer, "signed_for": recipient, "message": action.exact_message}
        responses = self.cores[recipient].on_message_batch([InboundEvent(sender=signer, kind="signed_message", signature_payload=payload, signed_for=recipient, signed_message=action.exact_message)])
        for response in responses:
            queue.append((recipient, response))

    @staticmethod
    def _score_submission(actor: str, action: SubmitSignature, scenario: RoundScenario, report: RoundReport) -> None:
        payload = action.signature_payload
        if not isinstance(payload, dict) or payload.get("signed_for") != actor or payload.get("message") != scenario.players[actor].exact_message:
            return
        report.players[actor].signatures_submitted += 1
        report.players[actor].score += 1

    @staticmethod
    def _validate_scenario(scenario: RoundScenario, names: tuple[str, ...]) -> None:
        known = set(names)
        for name, spec in scenario.players.items():
            if not spec.exact_message:
                raise ValueError(f"empty message for {name}")
            if not set(spec.collect_from) <= known - {name}:
                raise ValueError(f"invalid collect_from entry for {name}")
            if not set(spec.authorized_players) <= known - {name}:
                raise ValueError(f"invalid authorized player for {name}")


def balanced_exact_name_scenario(round_id: str = "1") -> RoundScenario:
    """Return a four-player smoke test where everyone can safely earn two points."""

    names = ("aria", "dex", "nova", "sol")
    next_player = {"aria": "dex", "dex": "nova", "nova": "sol", "sol": "aria"}
    messages = {"aria": "A giraffe joined a marching band as the triangle player.", "dex": "Bananas are hosting a fashion runway in my fridge.", "nova": "A moonlit penguin ordered soup at midnight.", "sol": "A brass robot planted roses beside the library."}
    players: dict[str, PlayerRound] = {}
    for name in names:
        authorized = next_player[name]
        expected_signer = next(player for player, target in next_player.items() if target == name)
        players[name] = PlayerRound(messages[name], (expected_signer,), (authorized,), frozenset({authorized}))
    return RoundScenario(round_id=round_id, players=players)
