import unittest
from types import SimpleNamespace

from projects.ultratrain.async_distillation_policy import AsyncDistillationPlan, AsyncDistillationStatus
from projects.ultratrain.trl_async_distillation_adapter import (
    AsyncDistillationAdapterError,
    adapt_trl_async_distillation,
)


class TRLAsyncDistillationAdapterTests(unittest.TestCase):
    def recipe(self, **overrides):
        values = {
            "method": "distillation",
            "training_engine": "trl",
            "executable": True,
            "runtime_args": {"teacher_provider": "vllm"},
            "environment": {"X": "1"},
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    def plan(self, status=AsyncDistillationStatus.SUPPORTED):
        return AsyncDistillationPlan(
            status=status,
            config_kwargs={
                "teacher_top_k": 8,
                "teacher_server_urls": {"default": "http://127.0.0.1:8001"},
            },
            decisions=("async_distillation.upstream_selected",),
        )

    def test_green_plan_materializes_upstream_async_classes(self):
        output = adapt_trl_async_distillation(self.recipe(), self.plan(), trl_version="1.13.0")
        self.assertEqual(
            output.trainer_class,
            "trl.experimental.async_distillation.AsyncDistillationTrainer",
        )
        self.assertEqual(
            output.config_class,
            "trl.experimental.async_distillation.AsyncDistillationConfig",
        )
        self.assertEqual(output.runtime_args["weight_delta_transport"], "full_nccl")

    def test_planner_must_have_selected_vllm_teacher(self):
        with self.assertRaises(AsyncDistillationAdapterError):
            adapt_trl_async_distillation(
                self.recipe(runtime_args={"teacher_provider": "external"}),
                self.plan(),
                trl_version="1.13.0",
            )

    def test_needs_canary_plan_cannot_materialize(self):
        with self.assertRaises(AsyncDistillationAdapterError):
            adapt_trl_async_distillation(
                self.recipe(),
                self.plan(AsyncDistillationStatus.NEEDS_CANARY),
                trl_version="1.13.0",
            )

    def test_non_executable_compiled_recipe_is_blocked(self):
        with self.assertRaises(AsyncDistillationAdapterError):
            adapt_trl_async_distillation(
                self.recipe(executable=False), self.plan(), trl_version="1.13.0"
            )

    def test_exact_trl_identity_is_required(self):
        with self.assertRaises(AsyncDistillationAdapterError):
            adapt_trl_async_distillation(self.recipe(), self.plan(), trl_version="1.13.1")

    def test_environment_is_preserved_and_policy_is_not_mutated(self):
        plan = self.plan()
        output = adapt_trl_async_distillation(self.recipe(), plan, trl_version="1.13.0")
        self.assertEqual(output.environment, {"X": "1"})
        output.config_kwargs["teacher_top_k"] = 64
        self.assertEqual(plan.config_kwargs["teacher_top_k"], 8)


if __name__ == "__main__":
    unittest.main()
