import unittest
from types import SimpleNamespace

from projects.ultratrain.remote_distillation_bridge import (
    RemoteBridgeStatus,
    TeacherLogitsTransportProfile,
    estimate_logits_chunk_bytes,
    plan_remote_distillation_bridge,
)
from projects.ultratrain.teacher_provider import (
    TeacherEndpoint,
    TeacherProviderPlan,
    TeacherProviderStatus,
)


class RemoteDistillationBridgeTests(unittest.TestCase):
    def recipe(self):
        return SimpleNamespace(method="distillation", training_engine="trl", executable=True)

    def teacher(self, status=TeacherProviderStatus.SUPPORTED):
        return TeacherProviderPlan(
            provider_kind="remote",
            status=status,
            endpoint=TeacherEndpoint(
                provider_id="teacher-provider",
                base_url="https://teacher.example.test",
                protocol="ultratrain.teacher-logits/v1",
            ),
            evidence=("canary://teacher",),
            fallback_teacher_model="local/teacher",
        )

    def transport(self, **overrides):
        values = {
            "protocol": "ultratrain.teacher-logits/v1",
            "streaming_full_vocab_logits": True,
            "bounded_chunk_tokens": 32,
            "accepts_attention_mask": True,
            "completion_alignment_verified": True,
            "numeric_equivalence_canary": True,
            "binary_or_tensor_transport": True,
        }
        values.update(overrides)
        return TeacherLogitsTransportProfile(**values)

    def test_json_v1_without_streaming_is_not_training_ready(self):
        plan = plan_remote_distillation_bridge(
            self.recipe(),
            self.teacher(),
            TeacherLogitsTransportProfile("ultratrain.teacher-logits/v1"),
            trl_version="1.13.0",
        )
        self.assertEqual(plan.status, RemoteBridgeStatus.NEEDS_CANARY)
        self.assertIn("teacher_streaming_full_vocab_logits", plan.canaries)

    def test_vlm_is_blocked_until_protocol_carries_multimodal_inputs(self):
        plan = plan_remote_distillation_bridge(
            self.recipe(), self.teacher(), self.transport(), trl_version="1.13.0", student_is_vlm=True
        )
        self.assertEqual(plan.status, RemoteBridgeStatus.UNSUPPORTED)
        self.assertIn("bridge.remote_vlm.protocol_not_supported", plan.rules)

    def test_green_text_bridge_pins_upstream_compute_loss_hook(self):
        plan = plan_remote_distillation_bridge(
            self.recipe(), self.teacher(), self.transport(), trl_version="1.13.0", vocab_size=32000
        )
        self.assertEqual(plan.status, RemoteBridgeStatus.SUPPORTED)
        self.assertEqual(plan.hook, "_compute_loss")
        self.assertEqual(plan.chunk_tokens, 32)

    def test_teacher_needs_canary_propagates(self):
        teacher = TeacherProviderPlan(
            provider_kind="remote",
            status=TeacherProviderStatus.NEEDS_CANARY,
            endpoint=self.teacher().endpoint,
            canaries=("teacher_logits_contract",),
        )
        plan = plan_remote_distillation_bridge(
            self.recipe(), teacher, self.transport(), trl_version="1.13.0"
        )
        self.assertEqual(plan.status, RemoteBridgeStatus.NEEDS_CANARY)
        self.assertIn("teacher_logits_contract", plan.canaries)

    def test_local_fallback_propagates(self):
        plan = plan_remote_distillation_bridge(
            self.recipe(), self.teacher(TeacherProviderStatus.FALLBACK), self.transport(), trl_version="1.13.0"
        )
        self.assertEqual(plan.status, RemoteBridgeStatus.FALLBACK)
        self.assertEqual(plan.strategy, "local_teacher_fallback")
        self.assertEqual(plan.fallback_teacher_model, "local/teacher")

    def test_protocol_mismatch_is_unsupported(self):
        plan = plan_remote_distillation_bridge(
            self.recipe(), self.teacher(), self.transport(protocol="teacher-logits/v2"), trl_version="1.13.0"
        )
        self.assertEqual(plan.status, RemoteBridgeStatus.UNSUPPORTED)

    def test_chunk_memory_budget_requires_canary(self):
        plan = plan_remote_distillation_bridge(
            self.recipe(),
            self.teacher(),
            self.transport(bounded_chunk_tokens=1024),
            trl_version="1.13.0",
            vocab_size=200000,
            max_chunk_bytes=64 * 1024 * 1024,
        )
        self.assertEqual(plan.status, RemoteBridgeStatus.NEEDS_CANARY)
        self.assertIn("teacher_logits_chunk_memory_budget", plan.canaries)

    def test_transfer_estimator(self):
        self.assertEqual(estimate_logits_chunk_bytes(1000, 32, 2), 64000)

    def test_exact_trl_version_is_required(self):
        plan = plan_remote_distillation_bridge(
            self.recipe(), self.teacher(), self.transport(), trl_version="1.13"
        )
        self.assertEqual(plan.status, RemoteBridgeStatus.UNSUPPORTED)

    def test_deterministic_json_does_not_serialize_endpoint_credentials(self):
        plan = plan_remote_distillation_bridge(
            self.recipe(), self.teacher(), self.transport(), trl_version="1.13.0"
        )
        payload = plan.to_json()
        self.assertEqual(payload, plan.to_json())
        self.assertNotIn("credential", payload)


if __name__ == "__main__":
    unittest.main()
