import unittest

from core.loop_factory.capabilities import (
    Availability, CapabilityRegistry, CostClass,
    WorkerCapability, default_cell000_registry,
)
from core.loop_factory.evidence import sha256_text


class CapabilityTests(unittest.TestCase):
    def test_free_first_ranking_is_deterministic(self):
        registry = CapabilityRegistry()
        registry.register(WorkerCapability(
            "paid", frozenset({"python.test"}), "cloud",
            CostClass.PAID, Availability.AVAILABLE, 0.10,
        ))
        registry.register(WorkerCapability(
            "local", frozenset({"python.test"}), "local",
            CostClass.LOCAL, Availability.AVAILABLE, 0.0,
        ))
        ids = [x.worker_id for x in registry.candidates("python.test", 1.0)]
        self.assertEqual(ids, ["local", "paid"])
    def test_unknown_hf_job_is_not_selected(self):
        ids = [
            x.worker_id
            for x in default_cell000_registry().candidates("gpu.burst", 100)
        ]
        self.assertNotIn("hf-jobs", ids)

    def test_sha256_is_stable(self):
        self.assertEqual(sha256_text("kai"), sha256_text("kai"))

    def test_unavailable_workers_are_filtered(self):
        registry = CapabilityRegistry()
        registry.register(WorkerCapability(
            "down", frozenset({"python.test"}), "local",
            CostClass.LOCAL, Availability.UNAVAILABLE, 0.0,
        ))
        self.assertEqual(registry.candidates("python.test", 10), [])
