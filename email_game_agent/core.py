"""Deterministic, protocol-independent action policy."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable

from .memory import AgentMemory
from .models import (
    Action,
    InboundEvent,
    RequestSignature,
    RoundAssignment,
    SignMessage,
    SubmitSignature,
)
from .resolver import HybridIdentityResolver, Resolution


class EmailGameCore:
    def __init__(
        self,
        agent_name: str,
        *,
        memory: AgentMemory | None = None,
        resolver: HybridIdentityResolver | None = None,
    ) -> None:
        self.agent_name = agent_name
        self.memory = memory or AgentMemory()
        self.resolver = resolver or HybridIdentityResolver()
        self.assignment: RoundAssignment | None = None
        self.authorized_senders: set[str] = set()
        self.unresolved_authorizations: dict[str, Resolution] = {}
        self._signed: set[tuple[str, str]] = set()
        self._submitted: set[tuple[str, str]] = set()

    def start_round(self, assignment: RoundAssignment) -> list[Action]:
        if not assignment.exact_message:
            raise ValueError("the assigned message must not be empty")
        self.assignment = assignment
        self._signed.clear()
        self._submitted.clear()
        self._resolve_authorizations()

        # Listed collectors go first; then exploit the rule that any signature scores.
        ordered = list(dict.fromkeys((*assignment.collect_from, *assignment.known_agents)))
        return [
            RequestSignature(recipient, assignment.exact_message)
            for recipient in ordered
            if recipient and recipient != self.agent_name
        ]

    def on_message_batch(self, events: Iterable[InboundEvent]) -> list[Action]:
        assignment = self._require_assignment()
        batch = list(events)

        # Observe the whole batch before making authorization decisions. Raw bodies
        # are intentionally excluded from memory and identity matching.
        for event in batch:
            if event.kind == "signature_request" and event.requested_message:
                self.memory.observe_request(
                    assignment.round_id, event.sender, event.requested_message
                )
        if self.unresolved_authorizations:
            self._resolve_authorizations()

        actions: list[Action] = []
        for event in batch:
            if event.kind == "signature_request":
                requested = event.requested_message
                key = (event.sender, requested or "")
                if (
                    requested
                    and event.sender in self.authorized_senders
                    and key not in self._signed
                ):
                    self._signed.add(key)
                    actions.append(SignMessage(event.sender, requested))
                continue

            if event.kind == "signed_message":
                if (
                    event.signature_payload is None
                    or event.signed_for != self.agent_name
                    or event.signed_message != assignment.exact_message
                ):
                    continue
                # The adapter/base class must cryptographically verify before or
                # while executing SubmitSignature.
                key = (event.sender, self._payload_fingerprint(event.signature_payload))
                if key not in self._submitted:
                    self._submitted.add(key)
                    actions.append(SubmitSignature(event.sender, event.signature_payload))
        return actions

    @staticmethod
    def _payload_fingerprint(payload: object) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=repr)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _resolve_authorizations(self) -> None:
        assignment = self._require_assignment()
        histories = self.memory.histories(before_round=assignment.round_id)
        self.authorized_senders.clear()
        self.unresolved_authorizations.clear()
        for reference in assignment.authorized_refs:
            result = self.resolver.resolve(reference, histories, assignment.known_agents)
            if result.player is None:
                self.unresolved_authorizations[reference] = result
            elif result.player != self.agent_name:
                self.authorized_senders.add(result.player)

    def _require_assignment(self) -> RoundAssignment:
        if self.assignment is None:
            raise RuntimeError("start_round must be called before processing messages")
        return self.assignment
