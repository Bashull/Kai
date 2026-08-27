import json
import unittest

from projects.ultratrain.scientific_evidence import ArtifactRef, DatasetRef, ScientificRunEnvelope


class ScientificEvidencePlaneTests(unittest.TestCase):
    def test_artifact_requires_sha256(self):
        with self.assertRaises(ValueError):
            ArtifactRef(uri="file:///model.gguf", sha256="", size_bytes=10, media_type="application/octet-stream")

    def test_artifact_requires_non_negative_size(self):
        with self.assertRaises(ValueError):
            ArtifactRef(uri="file:///model.gguf", sha256="a" * 64, size_bytes=-1, media_type="application/octet-stream")

    def test_dataset_ref_requires_identity(self):
        with self.assertRaises(ValueError):
            DatasetRef(dataset_id="", revision="main")

    def test_run_requires_stable_run_id(self):
        with self.assertRaises(ValueError):
            ScientificRunEnvelope(run_id="", recipe_digest="a" * 64)
    def test_recipe_digest_must_be_sha256(self):
        with self.assertRaises(ValueError):
            ScientificRunEnvelope(run_id="run-1", recipe_digest="bad")

    def test_parent_child_lineage_is_preserved(self):
        run = ScientificRunEnvelope(
            run_id="run-child",
            recipe_digest="b" * 64,
            parent_run_id="run-parent",
            child_run_ids=("run-grandchild",),
        )
        self.assertEqual(run.parent_run_id, "run-parent")
        self.assertEqual(run.child_run_ids, ("run-grandchild",))

    def test_dataset_and_artifact_refs_serialize(self):
        run = ScientificRunEnvelope(
            run_id="run-2",
            recipe_digest="c" * 64,
            datasets=(DatasetRef("ds", "rev1"),),
            artifacts=(ArtifactRef("file:///a", "d" * 64, 7, "application/octet-stream"),),
        )
        payload = json.loads(run.to_json())
        self.assertEqual(payload["datasets"][0]["dataset_id"], "ds")
        self.assertEqual(payload["artifacts"][0]["sha256"], "d" * 64)
    def test_provider_refs_are_optional_and_neutral(self):
        run = ScientificRunEnvelope(
            run_id="run-3",
            recipe_digest="e" * 64,
            provider_refs={"mlflow": "runs:/123"},
        )
        payload = json.loads(run.to_json())
        self.assertEqual(payload["provider_refs"]["mlflow"], "runs:/123")

    def test_hardware_runtime_metrics_and_evals_are_preserved(self):
        run = ScientificRunEnvelope(
            run_id="run-4",
            recipe_digest="f" * 64,
            hardware_profile={"gpu": "RTX"},
            runtime_profile={"torch": "2.x"},
            metrics={"loss": 0.1},
            evals={"score": 0.9},
        )
        payload = json.loads(run.to_json())
        self.assertEqual(payload["hardware_profile"]["gpu"], "RTX")
        self.assertEqual(payload["metrics"]["loss"], 0.1)
        self.assertEqual(payload["evals"]["score"], 0.9)


if __name__ == "__main__":
    unittest.main()
