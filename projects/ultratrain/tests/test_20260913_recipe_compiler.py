import copy
import json
import unittest
from types import SimpleNamespace

from projects.ultratrain.recipe_compiler import RecipeBlocked, compile_recipe


def _plan(
    *,
    status="SUPPORTED",
    engine="trl",
    long_profile=None,
    kernel="sdpa",
    decisions=(),
    canaries=(),
    rollout=None,
    teacher=None,
):
    return SimpleNamespace(
        status=status,
        method=SimpleNamespace(value="sft"),
        runtime=SimpleNamespace(
            training_engine=engine,
            rollout_provider=rollout,
            teacher_provider=teacher,
        ) if engine is not None else None,
        kernel=SimpleNamespace(backend=kernel, decisions=tuple(decisions)),
        long_context=SimpleNamespace(profile=long_profile or {}) if long_profile is not None else None,
        decisions=tuple(decisions),
        canaries=tuple(canaries),
        rules=(),
    )


class RecipeCompilerTests(unittest.TestCase):
    def test_request_is_not_mutated(self):
        request = {"profile_id": "p", "peft": {"lora": True}}
        original = copy.deepcopy(request)
        compile_recipe(_plan(), request)
        self.assertEqual(request, original)

    def test_trl_113_fastpath_maps_chunked_to_chunked_nll(self):
        plan = _plan(
            long_profile={"loss_type": "chunked", "target_tokens": 131072},
            decisions=("long_context.loss.trl_113_tensorcore_fastpath",),
        )
        recipe = compile_recipe(plan, {"profile_id": "p"})
        self.assertEqual(recipe.training_args["loss_type"], "chunked_nll")
        self.assertEqual(recipe.training_args["max_seq_length"], 131072)

    def test_transformers_runtime_does_not_claim_trl_chunked_nll(self):
        plan = _plan(
            engine="transformers",
            long_profile={"loss_type": "chunked", "target_tokens": 131072},
            decisions=("long_context.loss.trl_113_tensorcore_fastpath",),
        )
        recipe = compile_recipe(plan, {"profile_id": "p"})
        self.assertEqual(recipe.training_args["loss_type"], "chunked")

    def test_liger_and_verified_fastpath_are_materialized(self):
        plan = _plan(
            kernel="liger",
            decisions=("kernel.liger.preference_frozen_weight_fastpath",),
        )
        recipe = compile_recipe(plan, {"profile_id": "p"})
        self.assertTrue(recipe.training_args["use_liger_kernel"])
        self.assertTrue(recipe.training_args["liger_preference_frozen_weight_fastpath"])

    def test_region_remat_requires_policy_canary_before_executable(self):
        request = {
            "profile_id": "p",
            "activation_checkpointing": "region_remat",
            "torchtitan_available": True,
            "torch_remat_available": True,
            "activation_save_regions": ["attention", "mlp"],
        }
        recipe = compile_recipe(_plan(), request)
        self.assertFalse(recipe.executable)
        self.assertIn("torchtitan_region_remat", recipe.canaries)
        with self.assertRaises(RecipeBlocked):
            compile_recipe(_plan(), request, require_executable=True)

    def test_verified_region_remat_materializes_regions_and_rng_mode(self):
        request = {
            "profile_id": "p",
            "activation_checkpointing": "region_remat",
            "torchtitan_available": True,
            "torch_remat_available": True,
            "region_remat_canary_passed": True,
            "activation_save_regions": ["attention", "mlp"],
            "preserve_rng_state": False,
        }
        recipe = compile_recipe(_plan(), request, require_executable=True)
        self.assertEqual(recipe.training_args["activation_checkpointing"], "region_remat")
        self.assertEqual(recipe.training_args["activation_save_regions"], ["attention", "mlp"])
        self.assertEqual(recipe.training_args["region_remat_rng_mode"], "explicit_hooks")

    def test_blocked_plan_never_becomes_executable(self):
        recipe = compile_recipe(_plan(status="NEEDS_CANARY", canaries=("runtime",)), {"profile_id": "p"})
        self.assertFalse(recipe.executable)
        self.assertIn("runtime", recipe.canaries)
        with self.assertRaises(RecipeBlocked):
            compile_recipe(_plan(status="NEEDS_CANARY"), {"profile_id": "p"}, require_executable=True)

    def test_attention_and_runtime_boundary_are_preserved(self):
        request = {
            "profile_id": "p",
            "attention": "sdpa",
            "capability_runtime": {
                "provider_id": "unsloth-2026.9.4",
                "isolation": "process",
                "requires_isolation": True,
                "conflicts": ["canonical:trl>=1.13.0"],
            },
        }
        recipe = compile_recipe(_plan(), request)
        self.assertEqual(recipe.training_args["attn_implementation"], "sdpa")
        self.assertEqual(recipe.runtime_args["provider_id"], "unsloth-2026.9.4")
        self.assertEqual(recipe.runtime_args["isolation"], "process")
        self.assertEqual(recipe.training_engine, "trl")

    def test_json_is_stable(self):
        recipe = compile_recipe(_plan(), {"profile_id": "p"})
        self.assertEqual(recipe.to_json(), recipe.to_json())
        self.assertEqual(json.loads(recipe.to_json())["profile_id"], "p")


if __name__ == "__main__":
    unittest.main()
