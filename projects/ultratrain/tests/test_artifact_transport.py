import hashlib
import unittest

from projects.ultratrain.artifact_transport import (
    ArtifactResolver,
    TransportFailure,
    TransportPolicy,
)
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

    def test_non_retryable_403_fails_once_and_preserves_diagnostic(self):
        attempts = 0

        def loader(ref):
            nonlocal attempts
            attempts += 1
            raise TransportFailure(
                "xet.forbidden",
                status_code=403,
                retryable=False,
                diagnostic="access denied by xorb edge",
            )

        resolver = ArtifactResolver(
            {"hf+xet": ("hf-xet", loader)},
            TransportPolicy(allowed_schemes=("hf+xet",), max_attempts=5),
        )
        with self.assertRaises(TransportFailure) as ctx:
            resolver.resolve(self._ref("hf+xet://repo/model.bin", b"x"))
        self.assertEqual(attempts, 1)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("access denied", ctx.exception.diagnostic)

    def test_retryable_transport_failure_can_retry_then_succeed(self):
        payload = b"weights"
        attempts = 0

        def loader(ref):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise TransportFailure("xet.url_expired", status_code=403, retryable=True)
            return payload

        resolver = ArtifactResolver(
            {"hf+xet": ("hf-xet", loader)},
            TransportPolicy(allowed_schemes=("hf+xet",), max_attempts=2),
        )
        result = resolver.resolve(self._ref("hf+xet://repo/model.bin", payload))
        self.assertEqual(attempts, 2)
        self.assertEqual(result.integrity.status, IntegrityStatus.VERIFIED)

    def test_retry_budget_exhaustion_preserves_last_failure(self):
        attempts = 0

        def loader(ref):
            nonlocal attempts
            attempts += 1
            raise TransportFailure("xet.transient", status_code=503, retryable=True)

        resolver = ArtifactResolver(
            {"hf+xet": ("hf-xet", loader)},
            TransportPolicy(allowed_schemes=("hf+xet",), max_attempts=3),
        )
        with self.assertRaises(TransportFailure) as ctx:
            resolver.resolve(self._ref("hf+xet://repo/model.bin", b"x"))
        self.assertEqual(attempts, 3)
        self.assertEqual(ctx.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
