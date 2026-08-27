import hashlib
import unittest

from projects.ultratrain.artifact_transport import ArtifactResolver, TransportPolicy
from projects.ultratrain.scientific_evidence import ArtifactRef, IntegrityStatus


class ArtifactTransportTests(unittest.TestCase):
    def _ref(self, uri: str, payload: bytes) -> ArtifactRef:
        return ArtifactRef(
            uri=uri,
            sha256=hashlib.sha256(payload).hexdigest(),
            size_bytes=len(payload),
            media_type="application/octet-stream",
        )

    def test_disallowed_scheme_is_blocked(self):
        resolver = ArtifactResolver({}, TransportPolicy(allowed_schemes=("file",)))
        with self.assertRaises(ValueError):
            resolver.resolve(self._ref("https://example/model.bin", b"x"))

    def test_missing_transport_is_blocked(self):
        resolver = ArtifactResolver({}, TransportPolicy(allowed_schemes=("memory",)))
        with self.assertRaises(ValueError):
            resolver.resolve(self._ref("memory://model", b"x"))

    def test_registered_transport_resolves_and_verifies(self):
        payload = b"weights"
        resolver = ArtifactResolver(
            {"memory": ("memory-test", lambda ref: payload)},
            TransportPolicy(allowed_schemes=("memory",)),
        )
        result = resolver.resolve(self._ref("memory://model", payload))
        self.assertEqual(result.integrity.status, IntegrityStatus.VERIFIED)
        self.assertEqual(result.transport_id, "memory-test")
        self.assertEqual(result.require_verified(), payload)

    def test_corrupt_payload_is_not_delivered(self):
        expected = b"weights"
        resolver = ArtifactResolver(
            {"memory": ("memory-test", lambda ref: b"corrupt")},
            TransportPolicy(allowed_schemes=("memory",)),
        )
        result = resolver.resolve(self._ref("memory://model", expected))
        self.assertNotEqual(result.integrity.status, IntegrityStatus.VERIFIED)
        with self.assertRaises(ValueError):
            result.require_verified()

    def test_transport_payload_over_policy_limit_is_blocked(self):
        payload = b"12345"
        resolver = ArtifactResolver(
            {"memory": ("memory-test", lambda ref: payload)},
            TransportPolicy(allowed_schemes=("memory",), max_bytes=4),
        )
        with self.assertRaises(ValueError):
            resolver.resolve(self._ref("memory://model", payload))

    def test_uri_without_scheme_is_blocked(self):
        resolver = ArtifactResolver({}, TransportPolicy(allowed_schemes=("memory",)))
        with self.assertRaises(ValueError):
            resolver.resolve(self._ref("model.bin", b"x"))

    def test_policy_requires_nonempty_allowed_schemes(self):
        with self.assertRaises(ValueError):
            TransportPolicy(allowed_schemes=())

    def test_policy_rejects_nonpositive_max_bytes(self):
        with self.assertRaises(ValueError):
            TransportPolicy(allowed_schemes=("memory",), max_bytes=0)


if __name__ == "__main__":
    unittest.main()
