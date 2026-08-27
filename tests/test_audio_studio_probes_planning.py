import json
import unittest
from pathlib import Path

from audio_studio.models import Availability, SongRequest
from audio_studio.planning import plan_dry_run
from audio_studio.providers import (
    AceStepAdapter,
    MiniMaxMusic3Adapter,
    ProbeTarget,
    ace_step_local_target,
    minimax_music_api_target,
    suno_platform_target,
    ReadOnlyCapabilityProbe,
    SunoV55Adapter,
)


def target(name, **kwargs):
    return ProbeTarget(
        provider_id=name,
        capabilities=frozenset({"text_to_music"}),
        runtime=kwargs.pop("runtime", "REMOTE"),
        cost_class=kwargs.pop("cost_class", "UNKNOWN"),
        **kwargs,
    )


class ReadOnlyProbeTests(unittest.TestCase):
    def test_unconfigured_probe_is_unknown_and_never_generates(self):
        snapshot = ReadOnlyCapabilityProbe(target("ace")).run()
        self.assertEqual(snapshot.availability, Availability.UNKNOWN)
        self.assertFalse(snapshot.evidence["generation_attempted"])
    def test_probe_maps_status_without_exposing_secret(self):
        probe = ReadOnlyCapabilityProbe(
            target(
                "minimax",
                status_url="https://status.invalid/health",
                credential_pointer="vault:minimax",
            ),
            credential_resolver=lambda pointer: pointer == "vault:minimax",
            status_reader=lambda url: 204,
        )
        snapshot = probe.run()
        self.assertEqual(snapshot.availability, Availability.AVAILABLE)
        self.assertEqual(snapshot.evidence["credential_state"], "PRESENT")
        self.assertNotIn("secret", snapshot.evidence)

    def test_missing_credential_blocks_before_endpoint(self):
        called = []
        probe = ReadOnlyCapabilityProbe(
            target(
                "suno",
                status_url="https://status.invalid/health",
                credential_pointer="vault:suno",
            ),
            credential_resolver=lambda pointer: False,
            status_reader=lambda url: called.append(url) or 200,
        )
        snapshot = probe.run()
        self.assertEqual(snapshot.availability, Availability.TOOL_BLOCKED)
        self.assertEqual(called, [])


    def test_expected_json_rejects_wrong_service_behind_http_200(self):
        probe = ReadOnlyCapabilityProbe(
            target(
                "ace",
                status_url="http://127.0.0.1:8001/health",
                expected_json={"data": {"status": "ok", "service": "ACE-Step API"}},
            ),
            status_reader=lambda url: (200, {"data": {"status": "ok", "service": "other"}}),
        )
        snapshot = probe.run()
        self.assertEqual(snapshot.availability, Availability.OFFLINE)
        self.assertEqual(snapshot.evidence["endpoint_state"], "INVALID_RESPONSE")

    def test_official_catalog_encodes_verified_boundaries(self):
        ace = ace_step_local_target()
        minimax = minimax_music_api_target()
        suno = suno_platform_target()
        self.assertEqual(ace.status_url, "http://127.0.0.1:8001/health")
        self.assertIn("2026-08-20", minimax.policy_blocker)
        self.assertIsNone(suno.status_url)
        self.assertEqual(
            suno.metadata["contract_status"],
            "PLATFORM_CONFIRMED_DOCS_AUTH_REQUIRED",
        )


class DryRunPlanningTests(unittest.TestCase):
    def request(self):
        return SongRequest(
            "fixture",
            {
                "core_identity": "festival EDM",
                "lyrics": "[Chorus]\nFly",
                "duration_seconds": 180,
            },
        )

    def test_blocked_report_contains_evidence_and_no_generation(self):
        providers = [
            AceStepAdapter("ace", ReadOnlyCapabilityProbe(target("ace"))),
            SunoV55Adapter("suno", ReadOnlyCapabilityProbe(target("suno"))),
        ]
        report = plan_dry_run(self.request(), providers)
        self.assertEqual(report.status, "BLOCKED")
        self.assertFalse(report.generation_attempted)
        self.assertEqual(len(report.snapshots), 2)

    def test_planned_report_prefers_verified_free_route(self):
        probe = ReadOnlyCapabilityProbe(
            target(
                "minimax",
                status_url="https://status.invalid/health",
                cost_class="FREE",
            ),
            status_reader=lambda url: 200,
        )
        report = plan_dry_run(
            self.request(),
            [MiniMaxMusic3Adapter("minimax", probe)],
        )
        self.assertEqual(report.status, "PLANNED")
        self.assertEqual(report.selected_provider, "minimax")
        self.assertEqual(report.compiled["model"], "music-3.0")
        self.assertIn("prompt", report.compiled)
        self.assertFalse(report.generation_attempted)

    def test_real_blueprint_fixtures_compile_for_all_providers(self):
        root = Path(__file__).parents[1] / "fixtures" / "blueprints"
        fixtures = sorted(root.glob("*.json"))
        self.assertEqual(len(fixtures), 2)
        available = lambda name: ReadOnlyCapabilityProbe(
            target(name, status_url="https://status.invalid/health"),
            status_reader=lambda url: 200,
        )
        adapters = [
            AceStepAdapter("ace", available("ace")),
            MiniMaxMusic3Adapter("minimax", available("minimax")),
            SunoV55Adapter("suno", available("suno")),
        ]
        for path in fixtures:
            blueprint = json.loads(path.read_text(encoding="utf-8"))
            request = SongRequest(blueprint.pop("case_id"), blueprint)
            for adapter in adapters:
                with self.subTest(path=path.name, provider=adapter.provider_id):
                    report = plan_dry_run(request, [adapter])
                    self.assertEqual(report.status, "PLANNED")
                    self.assertTrue(report.compiled)


if __name__ == "__main__":
    unittest.main()
