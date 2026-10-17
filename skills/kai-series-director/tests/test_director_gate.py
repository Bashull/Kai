import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from director_gate import evaluate_plan  # noqa: E402


def base_plan():
    return {
        'schema_version': 'kai.director.plan/0.4-candidate',
        'project_id': 'film-pilot-01', 'mode': 'film', 'gear': 'G2',
        'assets': [{'id': 'CHAR-A', 'kind': 'character', 'canon_ref': 'canon://film-pilot-01/char-a@1',
                    'state_version': 'v1', 'license': 'ORIGINAL', 'rights_evidence': 'rights://original-001'}],
        'shots': [{'id': 'S01', 'scene_id': 'C01', 'story_order': 1, 'edit_order': 1,
                   'production_order': 1, 'asset_refs': [{'asset_id': 'CHAR-A', 'state_version': 'v1'}],
                   'camera': {'axis_id': 'AXIS-01'}}],
        'provider_jobs': [], 'repair_cycles': [], 'gameplay': []
    }


class DirectorGateTests(unittest.TestCase):
    def test_plan_never_claims_runtime_acceptance_or_authorizes_generation(self):
        r = evaluate_plan(base_plan())
        self.assertEqual(r['status'], 'PLAN_READY')
        self.assertFalse(r['generation_authorized'])
        self.assertEqual(r['media_decode'], 'NOT_RUN')
        self.assertEqual(r['visual_review'], 'NOT_RUN')
        self.assertEqual(r['acceptance'], 'NOT_RUN')
        self.assertEqual(r['errors'], [])

    def test_unsupported_camera_alias_rejected(self):
        p = base_plan()
        p['shots'][0]['axis_exception'] = {'type': 'deliberate', 'reason': 'axis crossing'}
        r = evaluate_plan(p)
        self.assertEqual(r['status'], 'BLOCKED')
        self.assertTrue(any('axis_exception' in e for e in r['errors']))

    def test_valid_exception_requires_reason_and_evidence(self):
        p = base_plan()
        p['shots'][0]['camera']['exception'] = {'type': 'deliberate', 'reason': '', 'evidence': ''}
        self.assertTrue(any('camera.exception' in e for e in evaluate_plan(p)['errors']))
        p['shots'][0]['camera']['exception']['reason'] = 'subject reverses direction'
        p['shots'][0]['camera']['exception']['evidence'] = 'storyboard://s01-v2'
        self.assertFalse(evaluate_plan(p)['errors'])

    def test_missing_or_mismatched_asset_version_is_blocker(self):
        p = base_plan()
        p['shots'][0]['asset_refs'][0]['state_version'] = 'v0'
        self.assertTrue(any('state_version' in e for e in evaluate_plan(p)['errors']))
        p['shots'][0]['asset_refs'][0]['asset_id'] = 'UNKNOWN'
        self.assertTrue(any('UNKNOWN' in e for e in evaluate_plan(p)['errors']))

    def test_gameplay_never_accepted_on_cinematic_evidence(self):
        p = base_plan()
        p['mode'] = 'hybrid'
        p['gameplay'] = [{'id': 'G01', 'engine': 'Godot', 'asset_refs': ['CHAR-A']}]
        r = evaluate_plan(p)
        self.assertEqual(r['gameplay_status'], 'RUN_NOT_VERIFIED')
        self.assertIn('gameplay G01: reproducible engine run missing', r['blockers'])
        self.assertEqual(r['acceptance'], 'NOT_RUN')

    def test_gameplay_declared_trace_still_needs_external_verification(self):
        p = base_plan()
        p['mode'] = 'game'
        p['shots'] = []
        p['gameplay'] = [{'id': 'G01', 'engine': 'Godot', 'asset_refs': ['CHAR-A'],
                          'run_evidence': {'trace_sha256': 'a' * 64, 'build_sha256': 'b' * 64,
                                           'replayable': True, 'assertions_passed': True}}]
        r = evaluate_plan(p)
        self.assertEqual(r['status'], 'PLAN_READY')
        self.assertEqual(r['gameplay_status'], 'RECEIPT_DECLARED_UNVERIFIED')
        self.assertEqual(r['acceptance'], 'NOT_RUN')

    def test_unknown_licensing_blocks_delivery(self):
        p = base_plan()
        p['assets'][0]['license'] = 'UNKNOWN'
        p['assets'][0]['rights_evidence'] = ''
        r = evaluate_plan(p)
        self.assertTrue(any('rights' in x for x in r['blockers']))
        self.assertEqual(r['delivery_status'], 'RIGHTS_PENDING')

    def test_submit_unknown_reconciles_without_retransmission(self):
        p = base_plan()
        p['provider_jobs'] = [{'id': 'JOB01', 'status': 'SUBMIT_UNKNOWN'}]
        r = evaluate_plan(p)
        self.assertEqual(r['status'], 'BLOCKED')
        self.assertEqual(r['provider_actions'][0]['action'], 'RECONCILE_NO_RESUBMIT')

    def test_localized_repair_limit_blocks_further_retry(self):
        p = base_plan()
        p['repair_cycles'] = [{'target': 'S01:hand-left', 'attempts': 3, 'max_attempts': 3}]
        r = evaluate_plan(p)
        self.assertEqual(r['repair_actions'][0]['action'], 'ESCALATE_HUMAN')
        p['repair_cycles'][0]['attempts'] = 2
        r = evaluate_plan(p)
        self.assertEqual(r['repair_actions'][0]['action'], 'REPAIR_SCOPE_ONLY')

    def test_no_gameplay_required_for_film_only(self):
        r = evaluate_plan(base_plan())
        self.assertEqual(r['gameplay_status'], 'NOT_APPLICABLE')

    def test_rejects_duplicate_shot_ids(self):
        p = base_plan()
        p['shots'].append(copy.deepcopy(p['shots'][0]))
        self.assertTrue(any('duplicate shot id' in x for x in evaluate_plan(p)['errors']))

    def test_media_fields_do_not_prove_real_media_review(self):
        p = base_plan()
        p['shots'][0]['media_evidence'] = {'sha256': 'a' * 64, 'decoded': True,
                                           'reviewed': True, 'identity': 'PASS'}
        r = evaluate_plan(p)
        self.assertEqual(r['media_decode'], 'NOT_RUN')
        self.assertEqual(r['visual_review'], 'NOT_RUN')
        self.assertEqual(r['acceptance'], 'NOT_RUN')

    def test_invalid_job_and_mode_blocked(self):
        p = base_plan()
        p['mode'] = 'universal'
        p['provider_jobs'] = [{'id': 'J', 'status': '???'}]
        self.assertEqual(evaluate_plan(p)['status'], 'BLOCKED')

    def test_story_edit_and_production_orders_are_separate(self):
        p = base_plan()
        p['shots'].append(dict(p['shots'][0], id='S02', story_order=2, edit_order=0, production_order=3))
        self.assertEqual(evaluate_plan(p)['status'], 'PLAN_READY')

    def test_malformed_nested_references_return_blockers_without_crash(self):
        p = base_plan()
        p["shots"][0]["asset_refs"] = None
        r = evaluate_plan(p)
        self.assertEqual(r["status"], "BLOCKED")
        self.assertTrue(any("asset_refs" in x for x in r["errors"]))
        p = base_plan()
        p["mode"] = "game"
        p["shots"] = []
        p["gameplay"] = [{"id": "G01", "engine": "Godot", "asset_refs": None}]
        r = evaluate_plan(p)
        self.assertTrue(any("asset_refs" in x for x in r["errors"]))

    def test_trusted_receipt_not_inferred_from_fake_metadata(self):
        p = base_plan()
        p["shots"][0]["media_evidence"] = {"sha256":"a"*64, "decoded":True,
              "reviewed":True, "identity":"PASS", "consent":"YES"}
        self.assertEqual(evaluate_plan(p)["evidence_scope"], "CONTRACT_STATIC_ONLY")
        self.assertFalse(evaluate_plan(p)["generation_authorized"])

    def test_game_asset_reference_requires_known_asset(self):
        p = base_plan()
        p['mode'] = 'game'
        p['shots'] = []
        p['gameplay'] = [{'id': 'G01', 'engine': 'Godot', 'asset_refs': ['UNKNOWN']}]
        self.assertTrue(any('UNKNOWN' in x for x in evaluate_plan(p)['errors']))


if __name__ == '__main__':
    unittest.main()
