import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from benchmark_jsonl import DATASET, compact, sha
from preflight import SCHEMA
from review_validation import BOUNDARY_RECORDS_SHA256, deployment_rules, probe, replay


class DeploymentReviewTests(unittest.TestCase):
    def test_deployment_decision_matrix(self):
        for executor, approved, expected in (
            ("pipeline", True, ("satisfied", "satisfied")),
            ("agent", True, ("violated", "satisfied")),
            ("pipeline", False, ("satisfied", "violated")),
            ("agent", False, ("violated", "violated")),
            (None, True, ("unresolved", "satisfied")),
            ("agent", None, ("violated", "unresolved")),
        ):
            with self.subTest(executor=executor, approved=approved):
                self.assertEqual(
                    deployment_rules(executor, approved),
                    dict(zip(("executor", "approval"), expected)),
                )

    def test_replay_suppresses_only_findings_on_the_pinned_compliant_case(self):
        case = next(case for case in json.loads(DATASET.read_text())["cases"]
                    if case["id"] == "code-clean-boundary")
        self.assertEqual(sha(compact(case["records"])), BOUNDARY_RECORDS_SHA256)
        row = {"arm": "jsonl", "mode": "live", "model_requested": "qwen4b",
               "case": case["id"], "records_sha256": BOUNDARY_RECORDS_SHA256, "valid": True,
               "gold": [], "found": [["P1", "C1"], ["P1", "C2"]]}
        conflict = dict(row, records_sha256="different", gold=row["found"])
        rejected = dict(row, valid=False, found=[])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trials.jsonl"
            original = "\n".join(json.dumps(item) for item in (row, conflict, rejected)) + "\n"
            path.write_text(original)
            report = replay(path)
            self.assertEqual(path.read_text(), original)
        self.assertFalse(report["execution_authorized"])
        summary = report["arms"]["jsonl"]
        self.assertEqual(summary["before"], {"tp": 2, "fp": 2, "fn": 0, "exact": 1})
        self.assertEqual(summary["after"], {"tp": 2, "fp": 0, "fn": 0, "exact": 2})
        self.assertEqual(summary["suppressed"], {"P1/C1": 1, "P1/C2": 1})
        self.assertEqual(summary["valid"], 2)


class LiveReviewContractTests(unittest.TestCase):
    def call_probe(self, content, *, finish="stop", returned="gemma31b"):
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value = json.dumps({
            "model": returned, "choices": [{"finish_reason": finish, "message": {"content": content}}]
        }).encode()
        with patch.dict(os.environ, {"ADR_PRIMARY_API_KEY": "ignored"}, clear=True), \
                patch("urllib.request.build_opener", return_value=opener):
            report = probe("gemma31b", "http://127.0.0.1:8092/v1")
        return report, opener

    def test_production_schema_checked_for_each_case(self):
        report, opener = self.call_probe('{"findings":[]}')
        self.assertEqual([row["case"] for row in report["results"]], ["clean", "conflict"])
        self.assertTrue(all(row["valid"] for row in report["results"]))
        self.assertFalse(report["execution_authorized"])
        self.assertEqual(opener.open.call_count, 2)
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8092/v1/chat/completions")
        self.assertIsNone(request.get_header("Authorization"))
        self.assertEqual(json.loads(request.data)["response_format"], {
            "type": "json_schema",
            "json_schema": {"name": "adr_review", "strict": True, "schema": SCHEMA},
        })

    def test_incomplete_invalid_or_wrong_model_is_reported(self):
        bad_quote = json.dumps({"findings": [
            {"category": "conflict", "severity": "critical", "source": "ADR-0001.md",
             "quote": "invented text", "reason": "synthetic test"}
        ]})
        for content, settings, stage, details in (
            ('{"findings":[]}', {"finish": "length"}, "finish_reason", {"finish_reason": "length"}),
            ('{"findings":[]}', {"returned": "qwen4b"}, "model_identity", {"model_reported": "qwen4b"}),
            ('{"findings":', {}, "model_json", {"line": 1, "column": 13}),
            (bad_quote, {}, "review_validation", {"error_detail": "Ungrounded evidence quote"}),
        ):
            with self.subTest(content=content, settings=settings):
                report, _ = self.call_probe(content, **settings)
                for row in report["results"]:
                    self.assertFalse(row["valid"])
                    self.assertEqual(row["error_stage"], stage)
                    for key, value in details.items():
                        self.assertEqual(row[key], value)

    def test_probe_reports_http_status_without_provider_body(self):
        opener = MagicMock()
        opener.open.side_effect = HTTPError("http://127.0.0.1:8092/v1", 404, "private body", {}, None)
        with patch.dict(os.environ, {}, clear=True), \
                patch("urllib.request.build_opener", return_value=opener):
            report = probe("qwen27b", "http://127.0.0.1:8092/v1")
        for row in report["results"]:
            self.assertFalse(row["valid"])
            self.assertEqual(row["error_stage"], "http")
            self.assertEqual(row["http_status"], 404)
        self.assertNotIn("private body", json.dumps(report))
