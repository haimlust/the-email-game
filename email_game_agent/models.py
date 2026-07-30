"""Typed boundary objects shared by the strategy core and kit adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Union

from .opponents import RequestStyle


@dataclass(frozen=True)
class RoundAssignment:
    round_id: str
    exact_message: str
    collect_from: tuple[str, ...]
    authorized_refs: tuple[str, ...]
    known_agents: tuple[str, ...]


EventKind = Literal["signature_request", "signed_message", "other"]


@dataclass(frozen=True)
class InboundEvent:
    """A parsed event whose sender comes from the authenticated envelope.

    The adapter, not untrusted email text, must set these structured fields.
    """

    sender: str
    kind: EventKind
    body: str = ""
    requested_message: str | None = None
    signature_payload: Any | None = None
    signed_for: str | None = None
    signed_message: str | None = None


@dataclass(frozen=True)
class RequestSignature:
    recipient: str
    exact_message: str
    body: str = ""
    request_style: RequestStyle = "protocol"


@dataclass(frozen=True)
class SignMessage:
    recipient: str
    exact_message: str


@dataclass(frozen=True)
class SubmitSignature:
    signer: str
    signature_payload: Any


Action = Union[RequestSignature, SignMessage, SubmitSignature]
