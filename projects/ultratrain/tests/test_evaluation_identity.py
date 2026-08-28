import json
import unittest

from projects.ultratrain.scientific_evidence import DatasetRef, EvaluationRef, ScientificRunEnvelope


class EvaluationIdentityTests(unittest.TestCase):
    def test_evaluation_requires_engine_version(self):
        with self.assertRaises(ValueError):
            EvaluationRef(
                evaluator_id="inspect-ai",
                evaluator_version="",
                task_id="gsm8k",
                task_version="v1",
                dataset=DatasetRef("gsm8k", "rev-1"),
            )

    def test_evaluation_requires_task_version(self):
        with self.assertRaises(ValueError):
            EvaluationRef(
                evaluator_id="inspect-ai",
                evaluator_version="0.3.258",
                task_id="gsm8k",
                task_version="",
                dataset=DatasetRef("gsm8k", "rev-1"),
            )
    def test_evaluation_requires_immutable_dataset_revision(self):
        with self.assertRaises(ValueError):
            EvaluationRef(
                evaluator_id="mlflow-eval",
                evaluator_version="3.15.2",
                task_id="promotion-suite",
                task_version="2026-08-28",
                dataset=DatasetRef("eval-set"),
            )

    def test_envelope_serializes_evaluation_identity(self):
        evaluation = EvaluationRef(
            evaluator_id="inspect-ai",
            evaluator_version="0.3.258",
            task_id="gsm8k",
            task_version="v2",
            dataset=DatasetRef("gsm8k", "rev-42"),
        )
        envelope = ScientificRunEnvelope(
            run_id="run-1",
            recipe_digest="a" * 64,
            evaluation_refs=(evaluation,),
        )
        payload = json.loads(envelope.to_json())
        self.assertEqual(payload["evaluation_refs"][0]["evaluator_version"], "0.3.258")
        self.assertEqual(payload["evaluation_refs"][0]["dataset"]["revision"], "rev-42")


if __name__ == "__main__":
    unittest.main()
