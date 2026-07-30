"""Competition-day adapter template.

Copy this file next to the official starter kit and replace the marked mappings.
It intentionally does not invent method names that have not been released yet.
"""

from email_game_agent import EmailGameCore, InboundEvent, RoundAssignment


class PreparedAgentAdapter:
    """Embed this object inside the official `CustomAgent(BaseAgent)` class."""

    def __init__(self, agent_name: str) -> None:
        self.core = EmailGameCore(agent_name)

    def begin_round(self, official_assignment):
        assignment = RoundAssignment(
            round_id=str(official_assignment.round_id),
            exact_message=official_assignment.message,
            collect_from=tuple(official_assignment.collect_from),
            authorized_refs=tuple(official_assignment.authorized_to_sign_for),
            known_agents=tuple(official_assignment.players),
        )
        return self.core.start_round(assignment)

    def handle_batch(self, official_messages):
        events = [self._map_event(message) for message in official_messages]
        return self.core.on_message_batch(events)

    @staticmethod
    def _map_event(message) -> InboundEvent:
        raise NotImplementedError(
            "Map authenticated sender and parsed signature fields from the starter kit"
        )


# On release day, define `class CustomAgent(BaseAgent)` using the exact imports and
# callbacks in the official README. It should delegate decisions to
# PreparedAgentAdapter and execute each returned action using BaseAgent helpers.

