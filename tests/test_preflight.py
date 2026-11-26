import unittest
from preflight import run, validate_review, fixture_review

class TestPreflight(unittest.TestCase):
    def test_clean(self):
        r=run('clean','fixture');self.assertEqual(r['decision'],'ALLOW');self.assertFalse(r['execution_authorized']);self.assertEqual([x['role'] for x in r['reviews']],['triage','primary'])
    def test_conflict(self):
        r=run('conflict','fixture');self.assertEqual(r['decision'],'REVIEW');self.assertEqual([x['role'] for x in r['reviews']],['triage','primary','independent']);self.assertIsNone(r['contract_candidate'])
    def test_lint(self):
        r=run('incomplete','fixture');self.assertEqual(r['decision'],'REJECT');self.assertEqual(r['reviews'],[])
    def test_timeout(self):
        def fail(*a): raise TimeoutError()
        r=run('clean','fixture',fail);self.assertEqual(r['decision'],'REVIEW');self.assertFalse(r['execution_authorized'])
    def test_bad_quote(self):
        def bad(*a): return {'findings':[{'category':'risk','severity':'critical','source':'ADR-0002.md','quote':'invented evidence','reason':'test'}]},{}
        self.assertEqual(run('clean','fixture',bad)['decision'],'REVIEW')
    def test_invalid_json_shape(self):
        def bad(*a): return {'ready_for_agents':True},{}
        self.assertEqual(run('clean','fixture',bad)['decision'],'REVIEW')
    def test_high_risk_clean_still_escalates(self):
        def clean(*a): return {'findings':[]},{}
        r=run('conflict','fixture',clean);self.assertIn('independent',[x['role'] for x in r['reviews']]);self.assertEqual(r['decision'],'REVIEW');self.assertFalse(r['execution_authorized'])
class TestEndpointConfiguration(unittest.TestCase):
    def test_custom_local_ports(self):
        from preflight import validate_endpoint
        for url in ('http://127.0.0.1:8181/v1','http://localhost:9999/v1','http://[::1]:8089/v1'):
            self.assertEqual(validate_endpoint(url),url)
    def test_custom_https_ports_and_base_paths(self):
        from preflight import validate_endpoint
        for url in ('https://inference.example.org:8443/v1','https://review.example.org:9443/openai/v1'):
            self.assertEqual(validate_endpoint(url,'https-only'),url)
    def test_bad_endpoints(self):
        from preflight import validate_endpoint
        for url,policy in [('http://remote.example/v1','loopback-only'),('http://remote.example/v1','https-only'),('https://user:password@host/v1','https-only'),('https://host/v1?key=abc','https-only'),('https://host/v1#x','https-only'),('https://host:99999/v1','https-only'),('https://host/other','https-only'),('https://host/v1','unknown')]:
            with self.subTest(url=url,policy=policy),self.assertRaises(ValueError):
                validate_endpoint(url,policy)
    def test_timeout_bounds(self):
        from unittest.mock import patch
        from preflight import inference_timeout
        with patch.dict('os.environ',{'ADR_TIMEOUT_SECONDS':'42'}):
            self.assertEqual(inference_timeout(),42)
        for val in ('0','301','abc'):
            with patch.dict('os.environ',{'ADR_TIMEOUT_SECONDS':val}),self.assertRaises(ValueError):
                inference_timeout()
    def test_always_independent(self):
        from unittest.mock import patch
        with patch.dict('os.environ',{'ADR_ROUTING_STRATEGY':'always_independent'},clear=True):
            r=run('clean','live',lambda *a: ({'findings':[]},{}))
        self.assertEqual([x['role'] for x in r['reviews']],['primary','independent'])
        self.assertEqual(r['decision'],'ALLOW')
    def test_invalid_adr_no_provider_even_with_missing_config(self):
        from unittest.mock import Mock,patch
        reviewer=Mock(side_effect=AssertionError('must not call'))
        with patch.dict('os.environ',{},clear=True):
            r=run('incomplete','live',reviewer)
        reviewer.assert_not_called()
        self.assertEqual(r['decision'],'REJECT')
    def test_secret_echo_redacted(self):
        from unittest.mock import patch
        with patch.dict('os.environ',{'ADR_PRIMARY_API_KEY':'secret-test-token'},clear=True):
            r=run('clean','live',lambda *a: ({'findings':[]},{'model_reported':'secret-test-token'}))
        self.assertEqual(r['reviews'][0]['model_reported'],'[REDACTED]')
    def test_missing_provider_fails_closed(self):
        from unittest.mock import patch
        with patch.dict('os.environ',{},clear=True):
            r=run('clean','live')
        self.assertEqual(r['decision'],'REVIEW')
        self.assertEqual([x['status'] for x in r['reviews']],['error','error'])
    def test_https_transport_payload(self):
        import json
        from unittest.mock import patch, MagicMock
        from preflight import SCHEMA, live_review
        response=MagicMock()
        response.__enter__.return_value.read.return_value=json.dumps({'model':'test-model','choices':[{'finish_reason':'stop','message':{'content':'{"findings":[]}'}}],'usage':{'prompt_tokens':10,'completion_tokens':3}}).encode()
        opener=MagicMock();opener.open.return_value=response
        with patch.dict('os.environ',{'ADR_ENDPOINT_POLICY':'https-only','ADR_PRIMARY_URL':'https://inference.example.org:8443/v1','ADR_PRIMARY_MODEL':'test-model','ADR_PRIMARY_API_KEY':'example-key','ADR_TIMEOUT_SECONDS':'42'},clear=True),patch('urllib.request.build_opener',return_value=opener):
            review,meta=live_review('primary',{'a':'synthetic'},'a')
        request=opener.open.call_args.args[0]
        self.assertEqual(request.full_url,'https://inference.example.org:8443/v1/chat/completions')
        self.assertEqual(request.get_header('Authorization'),'Bearer example-key')
        payload = json.loads(request.data)
        self.assertEqual(payload['model'], 'test-model')
        self.assertEqual(payload['response_format'], {
            'type': 'json_schema',
            'json_schema': {'name': 'adr_review', 'strict': True, 'schema': SCHEMA},
        })
        self.assertEqual(opener.open.call_args.kwargs['timeout'],42)
        self.assertEqual(review,{'findings':[]})
        self.assertEqual(meta['usage']['prompt_tokens'],10)
if __name__=='__main__': unittest.main()
