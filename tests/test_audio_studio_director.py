import unittest

from audio_studio.director import MusicDirector, RoutingError
from audio_studio.models import Availability, CapabilitySnapshot, SongRequest
from audio_studio.providers.fake import FakeMusicProvider


def provider(name, availability=Availability.AVAILABLE, *, caps=None, cost="FREE", runtime="REMOTE"):
    return FakeMusicProvider(
        name,
        CapabilitySnapshot(
            provider_id=name,
            availability=availability,
            capabilities=frozenset(caps or {"text_to_music"}),
            cost_class=cost,
            runtime=runtime,
            evidence={"probe": "test"},
        ),
    )


class MusicDirectorTests(unittest.TestCase):
    def request(self, **changes):
        values = {"case_id": "song-001", "blueprint": {"title": "Song"}}
        values.update(changes)
        return SongRequest(**values)
    def test_free_first_selects_free_route(self):
        director = MusicDirector([
            provider("paid", cost="PAID"),
            provider("ace", cost="FREE"),
        ])
        decision = director.plan(self.request())
        self.assertEqual(decision.provider_id, "ace")
        self.assertEqual(decision.compiled["case_id"], "song-001")

    def test_blocked_quota_is_not_called_offline(self):
        director = MusicDirector([
            provider("ace", Availability.BLOCKED_QUOTA),
            provider("minimax", cost="METERED"),
        ])
        decision = director.plan(self.request())
        self.assertEqual(decision.provider_id, "minimax")
        self.assertEqual(decision.rejected[0]["reason"], "BLOCKED_QUOTA")

    def test_local_only_rejects_remote_runtime(self):
        director = MusicDirector([
            provider("remote", runtime="REMOTE"),
            provider("local", runtime="LOCAL", cost="LOCAL"),
        ])
        decision = director.plan(self.request(local_only=True))
        self.assertEqual(decision.provider_id, "local")
    def test_missing_capability_is_evidenced(self):
        director = MusicDirector([
            provider("basic", caps={"text_to_music"}),
            provider("repair", caps={"text_to_music", "region_repair"}),
        ])
        request = self.request(required_capabilities=frozenset({"region_repair"}))
        decision = director.plan(request)
        self.assertEqual(decision.provider_id, "repair")
        self.assertIn("MISSING_CAPABILITIES", decision.rejected[0]["reason"])

    def test_no_route_reports_every_blocker(self):
        director = MusicDirector([
            provider("ace", Availability.BLOCKED_QUOTA),
            provider("suno", Availability.UNKNOWN),
        ])
        with self.assertRaisesRegex(RoutingError, "ace=BLOCKED_QUOTA"):
            director.plan(self.request())

    def test_requires_at_least_one_provider(self):
        with self.assertRaisesRegex(ValueError, "at least one"):
            MusicDirector([])


if __name__ == "__main__":
    unittest.main()