import unittest
from types import SimpleNamespace

from projects.ultratrain.trl_method_adapters import (
    TRLAdapterError,
    adapt_trl_distillation,
    adapt_trl_dpo,
    adapt_trl_grpo,
    adapt_trl_sft,
)


def recipe(method="sft", *, executable=True, engine="trl", args=None):
    return SimpleNamespace(
        schema_version="ultratrain.compiled_recipe/v1",
        method=method,
        executable=executable,
        training_engine=engine,
        training_args=args or {},
        runtime_args={"provider_id": "canonical"},
        environment={"X": "1"},
    )


class TRLMethodAdapterTests(unittest.TestCase):
    def test_sft_maps_portable_length_and_chunked_loss(self):
        out = adapt_trl_sft(recipe(args={"max_seq_length": 131072, "loss_type": "chunked_nll"}), {"packing": True}, trl_version="1.13.0")
        self.assertEqual(out.config_class, "trl.SFTConfig")
        self.assertEqual(out.config_kwargs["max_length"], 131072)
        self.assertEqual(out.config_kwargs["loss_type"], "chunked_nll")
        self.assertTrue(out.config_kwargs["packing"])

    def test_sft_blocks_chunked_nll_plus_liger(self):
        with self.assertRaises(TRLAdapterError):
            adapt_trl_sft(recipe(args={"loss_type": "chunked_nll", "use_liger_kernel": True}), {}, trl_version="1.13.0")

    def test_sft_preserves_verified_attention_as_model_init_kwarg(self):
        out = adapt_trl_sft(recipe(args={"attn_implementation": "sdpa"}), {}, trl_version="1.13.0")
        self.assertEqual(out.config_kwargs["model_init_kwargs"]["attn_implementation"], "sdpa")

    def test_dpo_uses_separate_preference_loss_namespace(self):
        out = adapt_trl_dpo(recipe("dpo", args={"max_seq_length": 65536}), {"dpo_loss_type": "sigmoid", "dpo_beta": 0.2}, trl_version="1.13.0")
        self.assertEqual(out.config_kwargs["max_length"], 65536)
        self.assertEqual(out.config_kwargs["loss_type"], ["sigmoid"])
        self.assertEqual(out.config_kwargs["beta"], 0.2)

    def test_dpo_does_not_copy_portable_language_model_loss(self):
        out = adapt_trl_dpo(recipe("dpo", args={"loss_type": "chunked_nll"}), {}, trl_version="1.13.0")
        self.assertNotIn("loss_type", out.config_kwargs)

    def test_dpo_padding_free_is_blocked_for_trl_113(self):
        with self.assertRaises(TRLAdapterError):
            adapt_trl_dpo(recipe("dpo"), {"padding_free": True}, trl_version="1.13.0")

    def test_non_executable_recipe_is_blocked(self):
        with self.assertRaises(TRLAdapterError):
            adapt_trl_sft(recipe(executable=False), {}, trl_version="1.13.0")

    def test_non_trl_engine_is_blocked(self):
        with self.assertRaises(TRLAdapterError):
            adapt_trl_sft(recipe(engine="transformers"), {}, trl_version="1.13.0")

    def test_exact_version_identity_required(self):
        with self.assertRaises(TRLAdapterError):
            adapt_trl_sft(recipe(), {}, trl_version="1.13")

    def test_runtime_and_environment_are_preserved(self):
        out = adapt_trl_sft(recipe(), {}, trl_version="1.13.0")
        self.assertEqual(out.runtime_args["provider_id"], "canonical")
        self.assertEqual(out.environment["X"], "1")


class TRLGRPODistillationAdapterTests(unittest.TestCase):
    def test_grpo_inprocess_maps_to_native_generation(self):
        r = recipe("grpo")
        r.runtime_args["rollout_provider"] = "trl_inprocess"
        out = adapt_trl_grpo(r, {"grpo_num_generations": 4}, trl_version="1.13.0")
        self.assertEqual(out.config_class, "trl.GRPOConfig")
        self.assertFalse(out.config_kwargs["use_vllm"])
        self.assertEqual(out.config_kwargs["num_generations"], 4)

    def test_grpo_vllm_is_materialized_only_from_runtime_route(self):
        r = recipe("grpo")
        r.runtime_args["rollout_provider"] = "vllm"
        out = adapt_trl_grpo(r, {"grpo_vllm_mode": "server", "grpo_vllm_server_base_url": "http://127.0.0.1:8000"}, trl_version="1.13.0")
        self.assertTrue(out.config_kwargs["use_vllm"])
        self.assertEqual(out.config_kwargs["vllm_mode"], "server")

    def test_grpo_rejects_generation_batch_size_plus_steps(self):
        r = recipe("grpo")
        r.runtime_args["rollout_provider"] = "trl_inprocess"
        with self.assertRaises(TRLAdapterError):
            adapt_trl_grpo(r, {"grpo_generation_batch_size": 16, "grpo_steps_per_generation": 2}, trl_version="1.13.0")

    def test_grpo_vllm_rejects_ds3_no_gather(self):
        r = recipe("grpo")
        r.runtime_args["rollout_provider"] = "vllm"
        with self.assertRaises(TRLAdapterError):
            adapt_trl_grpo(r, {"grpo_ds3_gather_for_generation": False}, trl_version="1.13.0")

    def test_distillation_local_teacher_maps_real_fields(self):
        r = recipe("distillation")
        r.runtime_args["teacher_provider"] = "external"
        out = adapt_trl_distillation(r, {"teacher_model_name_or_path": "teacher/model", "distillation_beta": 0.5}, trl_version="1.13.0")
        self.assertEqual(out.config_class, "trl.DistillationConfig")
        self.assertEqual(out.config_kwargs["teacher_model_name_or_path"], "teacher/model")
        self.assertEqual(out.config_kwargs["beta"], 0.5)
        self.assertNotIn("use_vllm", out.config_kwargs)

    def test_distillation_vllm_teacher_is_not_miswired_to_student_vllm(self):
        r = recipe("distillation")
        r.runtime_args["teacher_provider"] = "vllm"
        with self.assertRaises(TRLAdapterError):
            adapt_trl_distillation(r, {"teacher_model_name_or_path": "teacher/model"}, trl_version="1.13.0")

    def test_distillation_requires_teacher_identity(self):
        r = recipe("distillation")
        r.runtime_args["teacher_provider"] = "external"
        with self.assertRaises(TRLAdapterError):
            adapt_trl_distillation(r, {}, trl_version="1.13.0")

    def test_distillation_beta_bounds_are_enforced(self):
        r = recipe("distillation")
        r.runtime_args["teacher_provider"] = "external"
        with self.assertRaises(TRLAdapterError):
            adapt_trl_distillation(r, {"teacher_model_name_or_path": "teacher/model", "distillation_beta": 1.5}, trl_version="1.13.0")

    def test_distillation_blocks_cp_sp(self):
        r = recipe("distillation")
        r.runtime_args["teacher_provider"] = "external"
        r.runtime_args["sequence_parallelism"] = "cp"
        with self.assertRaises(TRLAdapterError):
            adapt_trl_distillation(r, {"teacher_model_name_or_path": "teacher/model"}, trl_version="1.13.0")


if __name__ == "__main__":
    unittest.main()
