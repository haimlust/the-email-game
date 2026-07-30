"""Run a deterministic four-player smoke match."""

from email_game_agent import EmailGameCore
from email_game_agent.simulator import MatchSimulator, balanced_exact_name_scenario


def main() -> None:
    scenario = balanced_exact_name_scenario()
    cores = {name: EmailGameCore(name) for name in scenario.players}
    print(MatchSimulator(cores).run_round(scenario).format_table())


if __name__ == "__main__":
    main()

