import unittest

from projects.ultratrain.compatibility_core import Decision, evaluate_profile


class SeptemberSecondUpdateWatchTests(unittest.TestCase):
    def test_transformers_affected_remote_custom_generate_is_unsupported(self):
        r = evaluate_profile({
            "profile_id": "p",
            "packages": {"transformers": "5.8.1"},
            "transformers": {"remote_custom_generate": True},
        })
        self.assertEqual(r.status, Decision.UNSUPPORTED)
        self.assertIn("transformers.custom_generate.preconsent_write", r.rules)

    def test_transformers_post_affected_range_can_continue(self):
        r = evaluate_profile({
            "profile_id": "p",
            "packages": {"transformers": "5.15.1"},
            "transformers": {"remote_custom_generate": True},
        })
        self.assertEqual(r.status, Decision.SUPPORTED)

    def test_mlflow_statsmodels_below_315_is_unsupported_even_when_private(self):
        r = evaluate_profile({
            "profile_id": "p",
            "tracking": {
                "provider": "mlflow",
                "version": "3.14.1",
                "network_exposure": "loopback",
                "statsmodels_flavor_load": True,
            },
        })
        self.assertEqual(r.status, Decision.UNSUPPORTED)
        self.assertIn("tracking.mlflow.statsmodels_pickle_guard", r.rules)

    def test_mlflow_statsmodels_315_is_not_blocked_by_pickle_guard(self):
        r = evaluate_profile({
            "profile_id": "p",
            "tracking": {
                "provider": "mlflow",
                "version": "3.15.0",
                "network_exposure": "loopback",
                "statsmodels_flavor_load": True,
            },
        })
        self.assertEqual(r.status, Decision.SUPPORTED)


if __name__ == "__main__":
    unittest.main()
