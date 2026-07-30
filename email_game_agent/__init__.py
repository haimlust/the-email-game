"""Protocol-independent strategy core for The Email Game."""

from .core import EmailGameCore
from .memory import AgentMemory
from .models import (
    InboundEvent,
    RequestSignature,
    RoundAssignment,
    SignMessage,
    SubmitSignature,
)
from .resolver import HybridIdentityResolver, Resolution
from .semantic import JsonSemanticScorer, build_identity_prompt
from .simulator import MatchSimulator, RoundScenario

__all__ = [
    "AgentMemory",
    "EmailGameCore",
    "HybridIdentityResolver",
    "InboundEvent",
    "JsonSemanticScorer",
    "MatchSimulator",
    "RequestSignature",
    "Resolution",
    "RoundAssignment",
    "RoundScenario",
    "SignMessage",
    "SubmitSignature",
    "build_identity_prompt",
]
