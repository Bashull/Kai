from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "kai_repo_5x5_fusion.py"


def load_module():
    spec = importlib.util.spec_from_file_location("kai_repo_5x5_fusion", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Repo5x5FusionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = load_module()

    def candidate(self, platform: str, index: int) -> dict[str, object]:
        return {
            "source_id": f"{platform.lower()}-{index}",
            "platform": platform,
            "repo_id": f"owner/project-{index}",
            "url": f"https://example.test/{platform.lower()}/{index}",
            "available": True,
            "license": "MIT",
            "capability": "visual-processing",
            "relevance": "Closes the declared gap",
            "evidence_type": ["architecture"],
            "scores": {
                "relevance": "PASS",
                "maturity": "PASS",
                "portability": "PASS",
                "license_safety": "PASS",
                "composability": "PASS",
            },
            "decision": "ADAPT",
        }

    def test_rejects_more_than_five_candidates_per_platform(self) -> None:
        github = [self.candidate("github", i) for i in range(6)]
        huggingface = [self.candidate("huggingface", i) for i in range(5)]

        with self.assertRaisesRegex(ValueError, "maximum 5"):
            self.mod.build_outputs(github, huggingface)

    def test_marks_undercovered_when_fewer_than_five_candidates_exist(self) -> None:
        github = [self.candidate("github", i) for i in range(3)]
        huggingface = [self.candidate("huggingface", i) for i in range(5)]

        outputs = self.mod.build_outputs(github, huggingface)

        self.assertEqual(outputs["inventory"]["coverage"]["github"], "UNDERCOVERED")
        self.assertEqual(outputs["inventory"]["coverage"]["huggingface"], "COVERED")

    def test_inventory_preserves_exact_source_ids_and_provenance(self) -> None:
        github = [self.candidate("github", i) for i in range(5)]
        huggingface = [self.candidate("huggingface", i) for i in range(5)]

        outputs = self.mod.build_outputs(github, huggingface)
        ids = [item["source_id"] for item in outputs["inventory"]["candidates"]]

        self.assertEqual(ids[:5], [f"github-{i}" for i in range(5)])
        self.assertEqual(ids[5:], [f"huggingface-{i}" for i in range(5)])
        self.assertEqual(outputs["inventory"]["protocol"], "KAI_REPOSITORY_5X5_V1")

    def test_scorecard_rejects_unknown_score_labels(self) -> None:
        bad = self.candidate("github", 0)
        bad["scores"]["relevance"] = "MAYBE"  # type: ignore[index]

        with self.assertRaisesRegex(ValueError, "score label"):
            self.mod.build_outputs([bad], [])

    def test_blueprint_accepts_only_known_adoption_decisions(self) -> None:
        bad = self.candidate("github", 0)
        bad["decision"] = "COPY_EVERYTHING"

        with self.assertRaisesRegex(ValueError, "decision"):
            self.mod.build_outputs([bad], [])

    def test_json_output_is_deterministic(self) -> None:
        github = [self.candidate("github", i) for i in range(5)]
        huggingface = [self.candidate("huggingface", i) for i in range(5)]

        first = self.mod.dumps_outputs(self.mod.build_outputs(github, huggingface))
        second = self.mod.dumps_outputs(self.mod.build_outputs(github, huggingface))

        self.assertEqual(first, second)
        json.loads(first)


if __name__ == "__main__":
    unittest.main()
