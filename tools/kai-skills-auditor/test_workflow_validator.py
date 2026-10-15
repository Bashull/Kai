"""Offline regression fixtures for the optional, pinned AICtrl donor candidate.

No service, workflow, git mutation, or model is invoked. Run this file directly
with --skill and --dependencies; Node and the three locked npm packages are
required. This is a validator test, not a provider execution test.
"""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


def task(node_id='leaf'):
    return {'id': node_id, 'type':'task','skill':'synthetic-skill@1.0.0',
            'taskType':'general','prompt':'Synthetic data only; do not execute.',
            'parameters':[]}


def workflow(nodes=None, **kwargs):
    return {'schemaVersion':'aictrl/workflow/v2', 'name':'synthetic-only',
            'nodes': [task()] if nodes is None else nodes, **kwargs}


def nested(counts):
    node = task()
    for i, n in enumerate(reversed(counts)):
        node = {'id':f'loop-{i}', 'type':'loop', 'maxIterations':n,
                'body':{'nodes':[node]}}
    return workflow([node])


class ValidatorTests(unittest.TestCase):
    skill = None
    dependencies = None
    receipts = []

    def setUp(self):
        if self.skill is None or self.dependencies is None:
            self.skipTest('Run directly with --skill and --dependencies for the optional donor fixture')

    def invoke(self, content=None, *, file=None, cwd=None, raw=None):
        with tempfile.TemporaryDirectory(prefix='kai-workflow-fixture-') as temp:
            target = Path(file) if file else Path(temp) / 'fixture.json'
            if file is None:
                target.write_text(raw if raw is not None else json.dumps(content))
            result = subprocess.run(['node', str(self.skill/'validate.mjs'), str(target)],
                                    cwd=cwd or self.dependencies, capture_output=True,
                                    text=True, timeout=20)
            self.receipts.append({'test':self.id().split('.')[-1],
                                  'file':Path(file).name if file else 'synthetic.json',
                                  'exit_code':result.returncode,
                                  'stdout':result.stdout,'stderr':result.stderr})
            return result

    def accept(self, doc):
        r = self.invoke(doc)
        self.assertEqual(r.returncode,0,r.stderr)

    def reject(self, doc, message):
        r = self.invoke(doc)
        self.assertEqual(r.returncode,1,r.stderr)
        self.assertIn(message,r.stderr)
        self.assertNotIn('TypeError:',r.stderr)

    def test_four_official_yaml_examples(self):
        paths=sorted((self.skill/'reference/examples').glob('*.yaml'))
        self.assertEqual(len(paths),4)
        for f in paths:
            with self.subTest(file=f.name):
                r=self.invoke(file=f);self.assertEqual(r.returncode,0,r.stderr)

    def test_minimal_task(self): self.accept(workflow())
    def test_two_loop_levels(self): self.accept(nested([2,2]))
    def test_three_loop_levels(self): self.accept(nested([2,2,2]))
    def test_iteration_budget_1000(self): self.accept(nested([10,10,10]))
    def test_four_loop_levels_rejected(self): self.reject(nested([2]*4),'nesting depth')
    def test_iteration_budget_exceeded(self): self.reject(nested([10,10,11]),'exceeds 1000')
    def test_zero_iterations_rejected(self): self.reject(nested([0]),'schema')
    def test_twenty_six_iterations_rejected(self): self.reject(nested([26]),'schema')
    def test_duplicate_id(self): self.reject(workflow([task(),task()]),'duplicate node id')
    def test_dangling_edge(self):
        self.reject(workflow(edges=[{'from':'leaf','to':'missing'}]),'edge.to')
    def test_cycle(self):
        self.reject(workflow([task('a'),task('b')],edges=[{'from':'a','to':'b'},
                     {'from':'b','to':'a'}]),'graph is cyclic')
    def test_nested_cycle(self):
        doc=nested([2]);body=doc['nodes'][0]['body'];body['nodes']=[task('a'),task('b')]
        body['edges']=[{'from':'a','to':'b'},{'from':'b','to':'a'}]
        self.reject(doc,'graph is cyclic')
    def test_malformed_edge_collection_reports_schema(self): self.reject(workflow(edges=4),'schema')
    def test_non_object_node_reports_schema(self): self.reject(workflow([None]),'schema')
    def test_missing_nodes(self): self.reject({'schemaVersion':'aictrl/workflow/v2','name':'bad'},'schema')
    def test_system_fields_forbidden(self): self.reject(workflow(status='published'),'schema')
    def test_unsupported_manual_node(self):
        self.reject(workflow([{'id':'human','type':'manual','checklistItems':['No effects']}]),'schema')
    def test_loop_while_and_until_exclusive(self):
        doc=nested([2]);doc['nodes'][0].update({'while':'true','until':'false'});self.reject(doc,'schema')
    def test_code_review_requires_single_pr_parameter(self):
        node=task();node.update({'taskType':'code-review','parameters':[
            {'name':'pr','type':'pull-request','required':True},
            {'name':'extra','type':'string'}]});self.reject(workflow([node]),'schema')
    def test_code_review_single_pr_parameter(self):
        node=task();node.update({'taskType':'code-review','parameters':[
            {'name':'pr','type':'pull-request','required':True}],
            'inputs':{'pr':{'value':'https://example.invalid/owner/repo/pull/1'}},
            'outputs':{'findings':'json'}});self.accept(workflow([node]))
    def test_missing_dependencies_is_blocked(self):
        with tempfile.TemporaryDirectory(prefix='kai-missing-node-deps-') as cwd:
            r=self.invoke(workflow(),cwd=cwd)
        self.assertEqual(r.returncode,2);self.assertIn('Missing validator dependencies',r.stderr)
    def test_missing_formats_is_blocked(self):
        with tempfile.TemporaryDirectory(prefix='kai-missing-formats-') as cwd:
            modules=Path(cwd)/'node_modules';modules.mkdir()
            for name in ('ajv','js-yaml'):
                (modules/name).symlink_to(self.dependencies/'node_modules'/name,target_is_directory=True)
            r=self.invoke(workflow(),cwd=cwd)
        self.assertEqual(r.returncode,2);self.assertIn('Missing validator dependencies',r.stderr)
    def test_malformed_json(self):
        r=self.invoke(raw='{invalid');self.assertEqual(r.returncode,2);self.assertIn('Could not read/parse',r.stderr)
    def test_retry_remains_explicit_server_limit(self):
        # The donor schema allows maxRetries > 0. Its guide says apply rejects
        # it. Preserve that boundary; an offline PASS must not imply publishability.
        node=task();node['retry']={'maxRetries':1,'backoffMs':0};self.accept(workflow([node]))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skill',type=Path,required=True)
    parser.add_argument('--dependencies',type=Path,required=True)
    parser.add_argument('--receipts',type=Path)
    args,rest=parser.parse_known_args()
    ValidatorTests.skill=args.skill.resolve();ValidatorTests.dependencies=args.dependencies.resolve()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(ValidatorTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if args.receipts:
        args.receipts.write_text(json.dumps({'tests':result.testsRun,
            'failures':len(result.failures),'errors':len(result.errors),
            'scope':'OFFLINE_VALIDATOR_ONLY_NO_PROVIDER_EXECUTION',
            'receipts':ValidatorTests.receipts},indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)
