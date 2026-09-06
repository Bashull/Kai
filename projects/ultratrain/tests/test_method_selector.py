import unittest

from projects.ultratrain.method_selector import MethodStatus, TrainingMethod, select_training_method


class MethodSelectorTests(unittest.TestCase):
    def test_explicit_valid_method_wins(self):
        result = select_training_method({"method": "grpo", "preference_pairs": True})
        self.assertEqual(result.method, TrainingMethod.GRPO)
        self.assertEqual(result.status, MethodStatus.SUPPORTED)
        self.assertIn("method.explicit", result.decisions)

    def test_preference_pairs_select_dpo(self):
        result = select_training_method({"preference_pairs": True})
        self.assertEqual(result.method, TrainingMethod.DPO)

    def test_reward_signal_select_grpo(self):
        result = select_training_method({"reward_signal": True})
        self.assertEqual(result.method, TrainingMethod.GRPO)

    def test_teacher_selects_distillation(self):
        result = select_training_method({"teacher_available": True})
        self.assertEqual(result.method, TrainingMethod.DISTILLATION)

    def test_no_signal_defaults_sft(self):
        result = select_training_method({})
        self.assertEqual(result.method, TrainingMethod.SFT)
        self.assertIn("method.sft_default", result.decisions)

    def test_multiple_implicit_signals_are_ambiguous(self):
        result = select_training_method({"preference_pairs": True, "reward_signal": True})
        self.assertIsNone(result.method)
        self.assertEqual(result.status, MethodStatus.NEEDS_CANARY)
        self.assertIn("method_signal_ambiguity", result.canaries)

    def test_invalid_explicit_method_is_unsupported(self):
        result = select_training_method({"method": "magic"})
        self.assertIsNone(result.method)
        self.assertEqual(result.status, MethodStatus.UNSUPPORTED)
        self.assertIn("method.explicit.invalid", result.rules)


if __name__ == "__main__":
    unittest.main()
