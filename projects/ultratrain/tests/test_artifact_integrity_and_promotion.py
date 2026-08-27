import hashlib
import unittest

from projects.ultratrain.scientific_evidence import (
    ArtifactRef,
    IntegrityStatus,
    ModelVersionRef,
    PromotionAlias,
    verify_artifact_bytes,
)


class ArtifactIntegrityAndPromotionTests(unittest.TestCase):
    def artifact(self, payload: bytes = b"weights") -> ArtifactRef:
        return ArtifactRef(
            uri="file:///model.bin",
            sha256=hashlib.sha256(payload).hexdigest(),
            size_bytes=len(payload),
            media_type="application/octet-stream",
        )

    def test_matching_bytes_are_verified(self):
        result = verify_artifact_bytes(self.artifact(), b"weights")
        self.assertEqual(result.status, IntegrityStatus.VERIFIED)
        self.assertTrue(result.allow_promotion)
    def test_size_mismatch_blocks_promotion(self):
        ref = self.artifact(b"weights")
        result = verify_artifact_bytes(ref, b"weight")
        self.assertEqual(result.status, IntegrityStatus.SIZE_MISMATCH)
        self.assertFalse(result.allow_promotion)

    def test_hash_mismatch_blocks_promotion(self):
        ref = self.artifact(b"weights")
        result = verify_artifact_bytes(ref, b"WEIGHTS")
        self.assertEqual(result.status, IntegrityStatus.HASH_MISMATCH)
        self.assertFalse(result.allow_promotion)

    def test_model_version_requires_stable_identity(self):
        with self.assertRaises(ValueError):
            ModelVersionRef(model_id="m", version_id="", run_id="r", artifact=self.artifact())

    def test_model_version_preserves_run_and_artifact_identity(self):
        ref = self.artifact()
        version = ModelVersionRef(model_id="m", version_id="v1", run_id="run-1", artifact=ref)
        self.assertEqual(version.run_id, "run-1")
        self.assertEqual(version.artifact.sha256, ref.sha256)
    def test_alias_requires_name_and_target(self):
        with self.assertRaises(ValueError):
            PromotionAlias(alias="", target_version_id="v1")
        with self.assertRaises(ValueError):
            PromotionAlias(alias="production", target_version_id="")

    def test_alias_is_a_pointer_not_model_identity(self):
        alias = PromotionAlias(alias="production", target_version_id="v1")
        rebound = alias.rebind("v2")
        self.assertEqual(alias.target_version_id, "v1")
        self.assertEqual(rebound.target_version_id, "v2")
        self.assertEqual(rebound.alias, "production")

    def test_rebind_rejects_empty_target(self):
        alias = PromotionAlias(alias="production", target_version_id="v1")
        with self.assertRaises(ValueError):
            alias.rebind("")


if __name__ == "__main__":
    unittest.main()
