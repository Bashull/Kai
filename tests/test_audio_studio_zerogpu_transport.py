import unittest

from audio_studio.execution import AuthorizationReceipt, ExecutionBlocked
from audio_studio.transports.gradio_zerogpu import (
    API_NAME,
    SPACE_ID,
    ZeroGpuCanaryRequest,
    compile_zerogpu_canary,
    execute_zerogpu_canary,
)


def receipt(*, allowed=True, provider_id="ace-step-1.5-zerogpu", cost_class="FREE"):
    return AuthorizationReceipt(
        provider_id=provider_id,
        allowed=allowed,
        reason="FREE_OR_LOCAL_ROUTE_APPROVED" if allowed else "BLOCKED",
        cost_class=cost_class,
        estimated_cost_usd=None,
        policy={"free_only": True},
        checked_at="2026-08-27T00:00:00+00:00",
    )


class ZeroGpuTransportTests(unittest.TestCase):
    def test_compile_is_pinned_and_free_canary_bounded(self):
        call = compile_zerogpu_canary(
            ZeroGpuCanaryRequest("instrumental Balearic house, warm bass"),
            receipt(),
        )
        self.assertEqual(call.space_id, SPACE_ID)
        self.assertEqual(call.api_name, API_NAME)
        self.assertEqual(call.contract_input_count, 49)
        self.assertEqual(call.max_attempts, 1)
        self.assertEqual(call.kwargs["selected_model"], "acestep-v15-turbo")
        self.assertEqual(call.kwargs["generation_mode"], "simple")
        self.assertEqual(call.kwargs["param_15"], 10)
        self.assertEqual(call.kwargs["param_16"], 1)
        self.assertFalse(call.kwargs["param_43"])
        self.assertFalse(call.kwargs["param_44"])

    def test_compile_fails_closed_without_valid_free_receipt(self):
        for bad in (
            receipt(allowed=False),
            receipt(provider_id="other"),
            receipt(cost_class="UNKNOWN"),
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ExecutionBlocked):
                    compile_zerogpu_canary(ZeroGpuCanaryRequest("test"), bad)

    def test_canary_limits_are_not_expandable(self):
        for request in (
            ZeroGpuCanaryRequest("test", duration_seconds=11),
            ZeroGpuCanaryRequest("test", batch_size=2),
        ):
            with self.subTest(request=request):
                with self.assertRaises(ValueError):
                    compile_zerogpu_canary(request, receipt())

    def test_execution_calls_submitter_exactly_once(self):
        call = compile_zerogpu_canary(ZeroGpuCanaryRequest("test"), receipt())
        seen = []
        result = execute_zerogpu_canary(call, lambda value: seen.append(value) or "ok")
        self.assertEqual(result, "ok")
        self.assertEqual(seen, [call])

    def test_gradio_submitter_makes_one_predict_call(self):
        from audio_studio.transports.gradio_zerogpu import submit_with_gradio_client
        call = compile_zerogpu_canary(ZeroGpuCanaryRequest("test"), receipt())
        seen = []

        class FakeClient:
            def __init__(self, *args, **kwargs):
                seen.append(("init", args, kwargs))

            def predict(self, **kwargs):
                seen.append(("predict", kwargs))
                return "audio.mp3"

        result = submit_with_gradio_client(
            call,
            token="present-not-serialized",
            download_files="/safe/output",
            client_factory=FakeClient,
        )
        self.assertEqual(result, "audio.mp3")
        self.assertEqual([item[0] for item in seen], ["init", "predict"])
        self.assertNotIn("token", call.to_dict())


if __name__ == "__main__":
    unittest.main()
