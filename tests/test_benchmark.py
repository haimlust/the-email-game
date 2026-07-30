import unittest

from email_game_agent.benchmark import BenchmarkCase, evaluate_cases
from email_game_agent.resolver import HybridIdentityResolver


class BenchmarkTests(unittest.TestCase):
    def test_report_separates_safe_abstention_from_wrong_authorization(self):
        cases = [BenchmarkCase("exact", "aria", "aria", {"aria": ("one",), "dex": ("two",)}), BenchmarkCase("uncertain", "completely unrelated clue", "dex", {"aria": ("one",), "dex": ("two",)})]
        report = evaluate_cases(cases, HybridIdentityResolver())
        self.assertEqual(report.correct, 1)
        self.assertEqual(report.abstentions, 1)
        self.assertEqual(report.wrong_authorizations, 0)


if __name__ == "__main__":
    unittest.main()

