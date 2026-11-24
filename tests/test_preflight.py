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
if __name__=='__main__': unittest.main()
