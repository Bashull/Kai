import unittest
from types import SimpleNamespace

from projects.ultratrain.trl_method_adapters import TRLAdapterError, adapt_trl_dpo, adapt_trl_sft


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


if __name__ == "__main__":
    unittest.main()
