import unittest
from benchmark_jsonl import encode,parse,score,aggregate,one_trial,DATASET
import json

class TestJsonlBenchmark(unittest.TestCase):
    def setUp(self):
        self.cases=json.loads(DATASET.read_text())["cases"]
        self.case=self.cases[1]
    def test_equal_information(self):
        rows=self.case["records"]
        self.assertEqual(json.loads(encode(rows,"json")),
                         [json.loads(l) for l in encode(rows,"jsonl").splitlines()])
    def test_both_fixture_formats(self):
        for case in self.cases:
            for arm in ("json","jsonl"):
                self.assertTrue(one_trial(case,arm,0,"fixture","",1024)["exact"])
    def test_truncation_invalid(self):
        for arm in ("json","jsonl"):
            for rows in ([{"type":"finding","evidence_id":"P1","constraint_id":"C1"}],
                         [{"type":"complete","count":1}]):
                with self.assertRaises(ValueError):
                    parse(encode(rows,arm),arm,self.case["records"])
    def test_unknown_id_invalid(self):
        rows=[{"type":"finding","evidence_id":"P99","constraint_id":"C1"},{"type":"complete","count":1}]
        with self.assertRaises(ValueError):
            parse(encode(rows,"jsonl"),"jsonl",self.case["records"])
    def test_duplicate_invalid(self):
        f={"type":"finding","evidence_id":"P1","constraint_id":"C1"}
        with self.assertRaises(ValueError):
            parse(encode([f,f,{"type":"complete","count":2}],"json"),"json",self.case["records"])
    def test_invalid_clean_not_exact(self):
        self.assertFalse(score(set(),set(),False)["exact"])
    def test_false_positive_and_negative(self):
        self.assertEqual(score({("P1","C2")},{("P1","C1")},True),
                         {"tp":0,"fp":1,"fn":1,"exact":False})
    def test_fixture_no_inference_metrics(self):
        rows=[one_trial(self.case,a,0,"fixture","",1024) for a in ("json","jsonl")]
        s=aggregate(rows)
        self.assertEqual(s["paired_trials"],1)
        self.assertEqual(s["paired_deltas"]["total_tokens"]["paired_n"],0)
        self.assertIsNone(s["paired_deltas"]["elapsed_seconds"]["median_jsonl_minus_json"])
