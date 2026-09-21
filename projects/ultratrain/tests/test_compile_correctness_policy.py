import unittest

from projects.ultratrain.compile_correctness_policy import (
    CompileCorrectnessStatus,
    evaluate_compile_correctness,
)


class CompileCorrectnessPolicyTests(unittest.TestCase):
    def test_compile_disabled_is_safe(self):
        result = evaluate_compile_correctness({"torch_compile": False})
        self.assertEqual(result.status, CompileCorrectnessStatus.SUPPORTED)

    def test_unknown_capture_shape_requires_canary(self):
        result = evaluate_compile_correctness({"torch_compile": True})
        self.assertEqual(result.status, CompileCorrectnessStatus.NEEDS_CANARY)
        self.assertIn("torch_compile_descriptor_closure_equivalence", result.canaries)

    def test_known_descriptor_capture_requires_canary_without_fix(self):
        result = evaluate_compile_correctness({
            "torch_compile": True,
            "captures_tensor_method_descriptor": True,
        })
        self.assertEqual(result.status, CompileCorrectnessStatus.NEEDS_CANARY)

    def test_verified_upstream_fix_allows_descriptor_capture(self):
        result = evaluate_compile_correctness({
            "torch_compile": True,
            "captures_tensor_method_descriptor": True,
            "descriptor_guard_fix_verified": True,
        })
        self.assertEqual(result.status, CompileCorrectnessStatus.SUPPORTED)

    def test_local_equivalence_canary_allows_descriptor_capture(self):
        result = evaluate_compile_correctness({
            "torch_compile": True,
            "captures_tensor_method_descriptor": True,
            "eager_compiled_equivalence_passed": True,
        })
        self.assertEqual(result.status, CompileCorrectnessStatus.SUPPORTED)

    def test_known_absence_of_descriptor_capture_is_safe(self):
        result = evaluate_compile_correctness({
            "torch_compile": True,
            "captures_tensor_method_descriptor": False,
        })
        self.assertEqual(result.status, CompileCorrectnessStatus.SUPPORTED)


if __name__ == "__main__":
    unittest.main()
