import unittest

from projects.ultratrain.compatibility_core import Decision, evaluate_profile


class TrackingSecurityPolicyTests(unittest.TestCase):
    def test_vulnerable_mlflow_with_webhooks_is_unsupported(self):
        r = evaluate_profile({
            "profile_id": "p",
            "tracking": {
                "provider": "mlflow",
                "version": "3.14.0",
                "webhooks_enabled": True,
                "network_exposure": "lan",
                "auth_mode": "basic",
                "egress_policy": "restricted",
            },
        })
        self.assertEqual(r.status, Decision.UNSUPPORTED)
        self.assertIn("tracking.mlflow.security_floor", r.rules)

    def test_exposed_mlflow_without_auth_is_unsupported(self):
        r = evaluate_profile({
            "profile_id": "p",
            "tracking": {
                "provider": "mlflow",
                "version": "3.15.0",
                "network_exposure": "lan",
                "auth_mode": "none",
            },
        })
        self.assertEqual(r.status, Decision.UNSUPPORTED)

    def test_public_mlflow_with_open_egress_needs_canary(self):
        r = evaluate_profile({
            "profile_id": "p",
            "tracking": {
                "provider": "mlflow",
                "version": "3.15.0",
                "network_exposure": "public",
                "auth_mode": "oidc",
                "egress_policy": "open",
                "webhooks_enabled": False,
            },
        })
        self.assertEqual(r.status, Decision.NEEDS_CANARY)
        self.assertIn("tracking_egress_isolation", r.canaries)

    def test_hardened_private_mlflow_is_supported(self):
        r = evaluate_profile({
            "profile_id": "p",
            "tracking": {
                "provider": "mlflow",
                "version": "3.15.0",
                "network_exposure": "private",
                "auth_mode": "oidc",
                "egress_policy": "restricted",
                "webhooks_enabled": False,
            },
        })
        self.assertEqual(r.status, Decision.SUPPORTED)

    def test_unknown_mlflow_version_requires_canary(self):
        r = evaluate_profile({
            "profile_id": "p",
            "tracking": {"provider": "mlflow"},
        })
        self.assertEqual(r.status, Decision.NEEDS_CANARY)
        self.assertIn("tracking_version_identity", r.canaries)

    def test_non_mlflow_tracking_is_not_subject_to_mlflow_floor(self):
        r = evaluate_profile({
            "profile_id": "p",
            "tracking": {
                "provider": "other",
                "version": "0.1.0",
                "network_exposure": "private",
            },
        })
        self.assertEqual(r.status, Decision.SUPPORTED)


if __name__ == "__main__":
    unittest.main()
