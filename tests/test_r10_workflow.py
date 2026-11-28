import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
import unittest

from experiments.r10 import context_abc


R10 = Path(__file__).resolve().parents[1] / "experiments" / "r10"


class SyntheticProvider(BaseHTTPRequestHandler):
    """Return controlled test responses using the records actually sent."""

    def log_message(self, *args):
        pass

    def send_json(self, value):
        payload = json.dumps(value).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        self.send_json({"data": [{"id": "qwen4b"}]} if self.path == "/v1/models" else {})

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.requests.append(request)
        schema = request["response_format"]["json_schema"]["schema"]
        prompt = request["messages"][1]["content"]
        if "findings" in schema["properties"]:
            result = {"findings": []}
        else:
            if prompt.startswith("- "):
                ids = re.findall(r"^- \*\*([^*]+)\*\* \(candidate\):", prompt, re.MULTILINE)
                has_context = "(constraint):" in prompt
            else:
                records = [json.loads(line) for line in prompt.splitlines()]
                ids = [row["id"] for row in records if row["kind"] == "candidate"]
                has_context = any(row["kind"] == "constraint" for row in records)
            result = {"assessments": [
                {"evidence_id": evidence_id, "status": "no_violation" if has_context else "insufficient_context",
                 "constraint_ids": [] if has_context else ["C1"]}
                for evidence_id in ids
            ]}
        self.send_json({
            "model": "qwen4b", "usage": {"prompt_tokens": 12, "completion_tokens": 4},
            "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(result)}}],
        })


class HostedProtocolTests(unittest.TestCase):
    def test_primary_decisions_and_constraint_references_are_scored_separately(self):
        cases = json.loads((R10 / "dataset.json").read_text())["cases"]
        case = next(item for item in cases if item["id"] == "adr-conflict")
        response = {"assessments": [
            {"evidence_id": "P1", "status": "violation", "constraint_ids": ["C1", "C9"]},
            {"evidence_id": "P2", "status": "insufficient_context", "constraint_ids": []},
        ]}
        normalized, discarded = context_abc.normalize(response, context_abc.visible_records(case, "B"))
        result = context_abc.score(case, "B", normalized)
        self.assertEqual(discarded, 1)
        self.assertEqual((result["tp"], result["fp"], result["fn"]), (1, 0, 1))
        self.assertEqual(result["constraint_refs"], {"tp": 1, "fp": 0, "fn": 1})
        self.assertEqual(result["positive_abstentions"], 1)
        self.assertFalse(result["exact"])
        response["assessments"][1]["evidence_id"] = "P1"
        with self.assertRaises(ValueError):
            context_abc.normalize(response, context_abc.visible_records(case, "B"))

    def test_both_protocols_generate_verified_artifacts(self):
        with ThreadingHTTPServer(("127.0.0.1", 0), SyntheticProvider) as server, TemporaryDirectory() as tmp:
            server.requests = []
            worker = Thread(target=server.serve_forever, daemon=True)
            worker.start()
            env = {key: value for key, value in os.environ.items()
                   if not key.startswith("R10_") and not key.startswith("GITHUB_")}
            env["R10_URL"] = f"http://127.0.0.1:{server.server_port}"
            try:
                for protocol in ("format-only", "context-abc"):
                    with self.subTest(protocol=protocol):
                        server.requests.clear()
                        root = Path(tmp) / protocol
                        command = [sys.executable, str(R10 / "runner.py"), "--output", str(root)]
                        if protocol == "context-abc":
                            command += ["--protocol", protocol]
                        subprocess.run(command, env=env, check=True, capture_output=True, timeout=15)
                        subprocess.run([sys.executable, str(R10 / "report.py"), str(root), "--mode", "local"],
                                       env=env, check=True, capture_output=True, timeout=15)
                        self.check_artifacts(root, protocol, server.requests)
            finally:
                server.shutdown()
                worker.join()

    def check_artifacts(self, root, protocol, requests):
        rows = [json.loads(line) for line in (root / "trials.jsonl").read_text().splitlines()]
        self.assertEqual(len(rows), 18)
        self.assertTrue(all(row["valid"] for row in rows))
        self.assertEqual(len(requests), 18)
        self.assertTrue(all(req["response_format"] == requests[0]["response_format"] for req in requests))
        report = json.loads((root / "comparison.json").read_text())
        self.assertEqual(report["protocol"], protocol)
        self.assertTrue((root / "report.md").is_file())
        for row in (root / "SHA256SUMS").read_text().splitlines():
            digest, name = row.split("  ", 1)
            self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), digest)
        if protocol == "format-only":
            self.assertEqual(set(report["arms"]), {"markdown", "json", "jsonl"})
            return
        self.assertEqual(set(report["arms"]), {"A", "B", "C"})
        self.assertEqual(report["arms"]["A"]["answered_candidates"], 0)
        self.assertEqual(report["arms"]["A"]["abstentions"], 12)
        self.assertEqual(report["arms"]["A"]["positive_abstentions"], 5)
        self.assertEqual(report["arms"]["A"]["invalid_constraint_refs"], 12)
        self.assertIsNone(report["arms"]["A"]["constraint_refs"])
        self.assertEqual(report["arms"]["B"]["answered_candidates"], 12)
        by_key = {(row["case"], row["arm"]): row for row in rows}
        for row, request in zip(rows, requests):
            prompt = request["messages"][1]["content"]
            if row["arm"] == "A":
                self.assertNotIn("(constraint):", prompt)
                self.assertNotEqual(row["records_sha256"], by_key[row["case"], "B"]["records_sha256"])
            if row["arm"] == "B":
                other = by_key[row["case"], "C"]
                self.assertEqual(row["records_sha256"], other["records_sha256"])
                self.assertNotEqual(row["input_sha256"], other["input_sha256"])
