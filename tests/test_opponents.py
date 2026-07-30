import unittest

from email_game_agent.opponents import OpponentBelief, OpponentModelBook


class OpponentBeliefTests(unittest.TestCase):
    def test_profiles_require_evidence_and_adapt_conservatively(self):
        responsive = OpponentBelief()
        unresponsive = OpponentBelief()
        for _ in range(3):
            responsive.observe(True)
            unresponsive.observe(False)

        self.assertEqual(responsive.profile, "responsive")
        self.assertEqual(responsive.request_style, "compact")
        self.assertAlmostEqual(responsive.response_probability, 0.8)
        self.assertEqual(unresponsive.profile, "unresponsive")
        self.assertEqual(unresponsive.request_style, "identity_hint")
        self.assertAlmostEqual(unresponsive.response_probability, 0.2)

    def test_round_outcome_is_binary_and_snapshot_round_trips(self):
        book = OpponentModelBook()
        book.record_request("aria")
        book.record_signature("aria")
        book.record_signature("aria")
        book.record_request("dex")
        book.finish_round()

        restored = OpponentModelBook.from_json(book.to_json())
        self.assertEqual(restored.snapshot(), book.snapshot())
        self.assertEqual(restored.belief_for("aria").successes, 1)
        self.assertEqual(restored.belief_for("dex").failures, 1)

    def test_request_composer_preserves_exact_message_once(self):
        book = OpponentModelBook()
        message = "A giraffe joined a marching band."
        style, body = book.compose_request("me", "aria", message)
        self.assertEqual(style, "protocol")
        self.assertEqual(body.count(message), 1)
        self.assertIn("server-authenticated", body)

    def test_required_players_remain_first_then_probability_breaks_ties(self):
        book = OpponentModelBook()
        for _ in range(3):
            book.belief_for("aria").observe(True)
            book.belief_for("nova").observe(False)
        ranked = book.rank_players(("nova", "aria", "dex"), required_players=("nova",))
        self.assertEqual(ranked, ["nova", "aria", "dex"])


if __name__ == "__main__":
    unittest.main()
