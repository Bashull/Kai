"""Exercise the real MCP SDK at the new operation/permission boundary."""
import json
from pathlib import Path
import tempfile
import unittest

from mcp import Client

from kai_meshy.core import Forge
from kai_meshy.sdk_server import Policy, create_server


class OfflineCLI:
    calls = 0

    def request(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError('NO_VENDOR_REQUEST_ALLOWED')

    def auth(self):
        raise AssertionError('NO_AUTH_REQUEST_ALLOWED')

    def balance(self):
        raise AssertionError('NO_BALANCE_REQUEST_ALLOWED')


def body(result):
    return json.loads(result.content[0].text)


class CapabilityFacadeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.cli = OfflineCLI()
        self.forge = Forge(Path(self.temp.name), cli=self.cli)

    async def asyncTearDown(self):
        self.temp.cleanup()

    async def test_schema_validation_and_quote_are_private_and_offline(self):
        async with Client(create_server(self.forge, Policy())) as client:
            listing = body(await client.call_tool('kai_meshy_capabilities', {}))
            self.assertTrue(listing['ok'])
            self.assertGreaterEqual(len(listing['result']), 30)
            description = body(await client.call_tool('kai_meshy_describe_capability', {'capability_id': 'image_to_3d.generate'}))
            self.assertIn('image_url', description['result']['request_schema']['properties'])
            self.assertTrue(description['result']['sources'])
            params = {'mode': 'preview', 'prompt': 'private synthetic canary statue', 'ai_model': 'meshy-7.1'}
            result = await client.call_tool('kai_meshy_validate_request', {'capability_id': 'text_to_3d.preview', 'parameters': params})
            self.assertFalse(result.is_error)
            value = body(result)['result']
            self.assertTrue(value['valid'])
            self.assertNotIn(params['prompt'], result.content[0].text)
            self.assertEqual(len(value['request_sha256']), 64)
            invalid = await client.call_tool('kai_meshy_validate_request', {'capability_id': 'text_to_3d.preview', 'parameters': {**params, 'invented_parameter': True}})
            self.assertTrue(invalid.is_error)
            quote = body(await client.call_tool('kai_meshy_quote', {'capability_id': 'text_to_3d.preview', 'parameters': params}))
            self.assertTrue(quote['ok'])
            self.assertEqual(quote['result']['permission'], 'NOT_GRANTED_BY_CATALOGUE')
            self.assertFalse(quote['result']['current_spend_authorized'])
            self.assertNotIn(params['prompt'], json.dumps(quote))
            names = {t.name for t in (await client.list_tools()).tools}
            self.assertNotIn('kai_meshy_plan_operation', names)
            self.assertNotIn('kai_meshy_submit_operation', names)
        self.assertEqual(self.cli.calls, 0)
        self.assertEqual(self.forge.list_jobs(), [])

    async def test_plan_does_not_submit_or_inherit_brick_workflow(self):
        policy = Policy(allow_writes=True, allow_spend=True)
        args = {'job_id': 'FREE_INFRA', 'capability_id': 'text_to_3d.preview',
                'parameters': {'mode': 'preview', 'prompt': 'synthetic cube'}, 'budget': 36}
        async with Client(create_server(self.forge, policy)) as client:
            denied = await client.call_tool('kai_meshy_plan_operation', args)
            self.assertTrue(denied.is_error)
            self.assertEqual(self.forge.list_jobs(), [])
            planned = await client.call_tool('kai_meshy_plan_operation', {**args, 'confirm': True})
            self.assertFalse(planned.is_error)
            self.assertEqual(body(planned)['result']['status'], 'PLANNED')
            self.assertEqual(self.forge.budget_status()['committed_or_actual_credits'], 0)
            legacy = body(await client.call_tool('kai_meshy_cycle', {'job_id': 'FREE_INFRA', 'confirm': True}))
            self.assertEqual(legacy['result']['next_action'], 'USE_CAPABILITY_OPERATION_LOOP')
            loop = body(await client.call_tool('kai_meshy_operation_cycle', {'job_id': 'FREE_INFRA', 'confirm': True}))
            self.assertFalse(loop['result']['paid_submission_performed'])
            self.assertEqual(loop['result']['operations'][0]['next_action'], 'EXPLICIT_AUTHORIZED_SUBMIT_REQUIRED')
            names = {t.name for t in (await client.list_tools()).tools}
            self.assertNotIn('kai_meshy_submit_operation', names)
            self.assertNotIn('kai_meshy_approve_operation_preview', names)
        self.assertEqual(self.cli.calls, 0)


if __name__ == '__main__':
    unittest.main()
