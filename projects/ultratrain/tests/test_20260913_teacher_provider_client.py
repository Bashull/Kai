import unittest

from projects.ultratrain.teacher_provider import TeacherEndpoint, TeacherIdentity
from projects.ultratrain.teacher_provider_client import TeacherProtocolError, TeacherProviderClient


class FakeTransport:
    def __init__(self, *, vocab=3, protocol="ultratrain.teacher-logits/v1", full=True):
        self.calls = []
        self.vocab = vocab
        self.protocol = protocol
        self.full = full

    def __call__(self, method, url, payload, timeout):
        self.calls.append((method, url, payload, timeout))
        if url.endswith("/v1/health"):
            return {"ok": True, "protocol": self.protocol}
        if url.endswith("/v1/identity"):
            return {"protocol": self.protocol, "model_id": "teacher/model", "revision": "abc", "tokenizer_id": "tok", "vocab_size": self.vocab}
        if url.endswith("/v1/logits"):
            ids = payload["input_ids"]
            return {"protocol": self.protocol, "full_vocab_logits": self.full, "vocab_size": self.vocab, "logits": [[0.0] * self.vocab for _ in ids]}
        raise AssertionError(url)


class TeacherProviderClientTests(unittest.TestCase):
    def endpoint(self):
        return TeacherEndpoint("remote", "https://teacher.example.test", auth_mode="bearer_ref", credential_ref="vault://teacher")

    def test_client_never_passes_credentials_to_transport(self):
        transport = FakeTransport()
        client = TeacherProviderClient(self.endpoint(), transport=transport)
        self.assertTrue(client.health())
        self.assertEqual(len(transport.calls[0]), 4)
        self.assertEqual(self.endpoint().credential_ref, "vault://teacher")

    def test_identity_contract(self):
        client = TeacherProviderClient(self.endpoint(), transport=FakeTransport())
        identity = client.identity()
        self.assertEqual(identity, TeacherIdentity("teacher/model", "abc", "tok", 3))

    def test_logits_requires_full_vocab_shape(self):
        client = TeacherProviderClient(self.endpoint(), transport=FakeTransport(vocab=3))
        batch = client.logits([1, 2])
        self.assertEqual(batch.token_count, 2)
        self.assertEqual(batch.vocab_size, 3)
        self.assertEqual(len(batch.logits[0]), 3)

    def test_partial_logprobs_are_rejected(self):
        client = TeacherProviderClient(self.endpoint(), transport=FakeTransport(full=False))
        with self.assertRaises(TeacherProtocolError):
            client.logits([1])

    def test_malformed_vocab_dimension_is_rejected(self):
        class Bad(FakeTransport):
            def __call__(self, method, url, payload, timeout):
                if url.endswith("/v1/logits"):
                    return {"protocol": self.protocol, "full_vocab_logits": True, "vocab_size": 3, "logits": [[0.0, 1.0]]}
                return super().__call__(method, url, payload, timeout)

        client = TeacherProviderClient(self.endpoint(), transport=Bad())
        with self.assertRaises(TeacherProtocolError):
            client.logits([1])

    def test_canary_is_green_only_when_all_contracts_match(self):
        client = TeacherProviderClient(self.endpoint(), transport=FakeTransport())
        expected = TeacherIdentity("teacher/model", "abc", "tok", 3)
        ev = client.run_canary(expected_identity=expected, student_tokenizer_id="tok", student_vocab_size=3, probe_input_ids=[1, 2], evidence_ref="canary://1")
        self.assertTrue(ev.health_ok)
        self.assertTrue(ev.identity_ok)
        self.assertTrue(ev.full_vocab_logits)
        self.assertTrue(ev.logits_contract_ok)

    def test_canary_records_failure_without_leaking_exception(self):
        client = TeacherProviderClient(self.endpoint(), transport=FakeTransport(protocol="wrong"))
        expected = TeacherIdentity("teacher/model", "abc", "tok", 3)
        ev = client.run_canary(expected_identity=expected, student_tokenizer_id="tok", student_vocab_size=3, probe_input_ids=[1], evidence_ref="canary://bad")
        self.assertFalse(ev.health_ok)
        self.assertFalse(ev.logits_contract_ok)
        self.assertEqual(ev.evidence_refs, ("canary://bad",))


if __name__ == "__main__":
    unittest.main()
