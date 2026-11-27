"""Replay measured deployment findings and probe the live preflight contract."""

import argparse
import json
import os
from pathlib import Path
from typing import Literal
from urllib.error import HTTPError

from benchmark_jsonl import ARMS, score
from preflight import CASES, ROOT, live_review, redact_report, validate_endpoint, validate_review


BOUNDARY_CASE = "code-clean-boundary"
BOUNDARY_RECORDS_SHA256 = "299f6a4214300a475bf41b46e0a6606e451c7136aa55cd637deede920805ec89"


def deployment_rules(executor: Literal["pipeline", "agent"] | None, approved: bool | None):
    """Evaluate rules using resolved facts from a trusted source. None is unresolved."""
    if executor not in ("pipeline", "agent", None) or (approved is not None and type(approved) is not bool):
        raise ValueError("Invalid deployment fact")
    return {
        "executor": {None: "unresolved", "pipeline": "satisfied", "agent": "violated"}[executor],
        "approval": {None: "unresolved", True: "satisfied", False: "violated"}[approved],
    }


def verified_findings(row, found):
    # These facts belong to the pinned synthetic fixture. Do not derive identity
    # or approval from a model's output or from the spelling of a real CI step.
    if (not row["valid"] or row["case"] != BOUNDARY_CASE
            or row.get("records_sha256") != BOUNDARY_RECORDS_SHA256):
        return found
    checks = deployment_rules(executor="pipeline", approved=True)
    rules = {("P1", "C1"): "approval", ("P1", "C2"): "executor"}
    return found - {pair for pair, rule in rules.items() if checks[rule] == "satisfied"}


def replay(path):
    """Re-score stored findings without rerunning inference or editing the logs."""
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if not rows or any(row["arm"] not in ARMS or row["mode"] != "live" for row in rows):
        raise ValueError("Expected saved live benchmark rows")
    models = {row["model_requested"] for row in rows}
    if len(models) != 1:
        raise ValueError("Expected one model per trial file")
    report = {"model": models.pop(), "arms": {}, "execution_authorized": False}
    for arm in ARMS:
        totals = {
            "rows": 0, "valid": 0, "changed_rows": 0, "suppressed": {"P1/C1": 0, "P1/C2": 0},
            "before": dict.fromkeys(("tp", "fp", "fn", "exact"), 0),
            "after": dict.fromkeys(("tp", "fp", "fn", "exact"), 0),
        }
        for row in (item for item in rows if item["arm"] == arm):
            gold = {tuple(pair) for pair in row["gold"]}
            found = {tuple(pair) for pair in row["found"]}
            verified = verified_findings(row, found)
            totals["rows"] += 1
            totals["valid"] += row["valid"]
            totals["changed_rows"] += verified != found
            for pair in found - verified:
                totals["suppressed"]["/".join(pair)] += 1
            for stage, findings in (("before", found), ("after", verified)):
                for name, value in score(findings, gold, row["valid"]).items():
                    totals[stage][name] += value
        report["arms"][arm] = totals
    return report


def probe(model, url):
    """Call the same provider and response validator used by preflight."""
    os.environ["ADR_PRIMARY_URL"] = validate_endpoint(url, "loopback-only")
    os.environ["ADR_ENDPOINT_POLICY"] = "loopback-only"
    os.environ["ADR_PRIMARY_MODEL"] = model
    os.environ.pop("ADR_PRIMARY_API_KEY", None)
    accepted = {path.name: path.read_text() for path in sorted((ROOT / "adr/accepted").glob("*.md"))}
    results = []
    for case in ("clean", "conflict"):
        candidate = CASES[case]
        sources = {**accepted, candidate: (ROOT / "adr/proposed" / candidate).read_text()}
        result = {"case": case, "valid": False}
        try:
            response, metadata = live_review("primary", sources, candidate, diagnostic=result)
            result["error_stage"] = "model_identity"
            if metadata["model_reported"] != model:
                raise ValueError("Reported model does not match the requested alias")
            result["error_stage"] = "review_validation"
            result.update(valid=True, findings=validate_review(response, sources))
            del result["error_stage"]
        except (OSError, ValueError, TypeError, KeyError, IndexError) as error:
            result["error_type"] = type(error).__name__
            if isinstance(error, HTTPError):
                result["http_status"] = error.code
            elif isinstance(error, json.JSONDecodeError):
                result.update(json_error=error.msg, line=error.lineno, column=error.colno)
            elif result.get("error_stage") in ("finish_reason", "model_identity", "review_validation"):
                # These messages are authored by the local validator.
                result["error_detail"] = str(error)
        results.append(result)
    return redact_report({"model": model, "results": results, "execution_authorized": False})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    replay_parser = subcommands.add_parser("replay", help="Re-score saved live trial files")
    replay_parser.add_argument("trials", nargs="+", type=Path)
    probe_parser = subcommands.add_parser("probe", help="Check the schema contract on a running model")
    probe_parser.add_argument("model", help="Exact alias served by llama-server")
    probe_parser.add_argument("--url", default="http://127.0.0.1:8092/v1")
    args = parser.parse_args()
    try:
        if args.command == "replay":
            result = [replay(path) for path in args.trials]
            status = 0
        else:
            result = probe(args.model, args.url)
            status = int(not all(row["valid"] for row in result["results"]))
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
