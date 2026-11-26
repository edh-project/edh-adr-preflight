#!/usr/bin/env python3
"""Inspect Gemma JSON failures and probe actor attribution in local ADR review."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from urllib.request import ProxyHandler, build_opener


REVISION = '38bc939a1c270667805bf42504c29096771a8048'
ENDPOINT = 'http://127.0.0.1:8092/v1'
MODELS = ('gemma31b', 'qwen27b', 'qwen4b')
ROOT = Path.home() / 'WORK' / '_edh'
MAX_TOKENS = 1024


def stress_cases(cases, model):
    clean = cases['code-clean-boundary']
    records = [dict(record) for record in clean['records']]
    p1 = next(record for record in records if record['id'] == 'P1')
    if p1['text'] != 'if approved is True: pipeline.deploy(patch)' or clean['expected']:
        raise ValueError('Unexpected actor boundary fixture')
    p1['text'] = 'if approved is True: agent.deploy(patch)'
    violating = dict(clean, id='code-actor-direct-deploy', records=records, expected=[['P1', 'C2']])
    if model == 'gemma31b':
        yield 'json', cases['code-clean']
        yield 'json', cases['adr-conflict']
    yield 'jsonl', clean
    yield 'jsonl', violating


def run_case(benchmark, arm, case, model):
    gold = {tuple(pair) for pair in case['expected']}
    found = set()
    row = {'case': case['id'], 'arm': arm, 'gold': sorted(gold), 'valid': False,
           'content': None, 'finish_reason': None, 'usage': {},
           'model_requested': model, 'model_reported': None,
           'input_sha256': benchmark.sha(benchmark.encode(case['records'], arm)),
           'prompt_sha256': benchmark.sha(benchmark.PROMPT + benchmark.FORMATS[arm])}
    started = time.monotonic()
    try:
        raw, finish, usage, reported = benchmark.live_request(case['records'], arm, model, MAX_TOKENS)
        row.update(content=raw, finish_reason=finish, usage=usage, model_reported=reported)
        if reported != model:
            raise ValueError(f'Expected response model {model}, got {reported!r}')
        if finish != 'stop':
            raise ValueError('Incomplete response')
        found = benchmark.parse(raw, arm, case['records'])
        row['valid'] = True
    except (OSError, ValueError, TypeError, KeyError, IndexError) as error:
        row.update(error_type=type(error).__name__, error_detail=str(error))
    row.update(benchmark.score(found, gold, row['valid']), found=sorted(found),
               elapsed_seconds=round(time.monotonic() - started, 6))
    return row


def summary(model, rows):
    lines = [f'# Actor boundary probe — {model}', '',
             f'Benchmark `{REVISION}` · output limit {MAX_TOKENS} tokens.', '',
             '| Format | Case | Finish | Valid | Exact | Gold | Found |',
             '| --- | --- | --- | --- | --- | --- | --- |']
    for row in rows:
        lines.append(f"| {row['arm']} | {row['case']} | {row['finish_reason']} | "
                     f"{row['valid']} | {row['exact']} | {row['gold']} | {row['found']} |")
    lines += ['', '## Model responses', '']
    for row in rows:
        lines += [f"### {row['case']} ({row['arm']})", '',
                  f"Parser outcome: {row.get('error_type', 'accepted')} {row.get('error_detail', '')}".rstrip(),
                  '', '```text', repr(row['content'])[:700].replace('```', '` ` `'), '```', '']
    lines += ['The initial code fixture and its variant differ only in the receiver of `deploy`. '
              'The full response strings are available in local `trials.jsonl`.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model', choices=MODELS, help='Alias of the model running on port 8092')
    parser.add_argument('--source', type=Path, default=ROOT / 'edh-4b-jsonl-pilot' / 'source')
    args = parser.parse_args()
    checkout = args.source.expanduser().resolve()
    git = ['git', '-C', str(checkout)]
    try:
        revision = subprocess.check_output([*git, 'rev-parse', 'HEAD'], text=True).strip()
        if revision != REVISION:
            raise ValueError(f'Expected benchmark revision {REVISION}, got {revision}')
        changes = subprocess.check_output([*git, 'status', '--porcelain', '--',
                                           'preflight.py', 'benchmark_jsonl.py', 'benchmarks'], text=True)
        if changes:
            raise ValueError('The benchmark or its fixtures have uncommitted changes')
        sys.path.insert(0, str(checkout))
        import benchmark_jsonl as benchmark

        opener = build_opener(ProxyHandler({}), benchmark.NoRedirect())
        with opener.open(ENDPOINT + '/models', timeout=5) as response:
            aliases = {model['id'] for model in json.load(response)['data']}
        if aliases != {args.model}:
            raise ValueError(f'Expected only alias {args.model}, got {sorted(aliases)}')

        os.environ.pop('ADR_PRIMARY_API_KEY', None)
        os.environ.update(ADR_PRIMARY_URL=ENDPOINT, ADR_ENDPOINT_POLICY='loopback-only',
                          ADR_TIMEOUT_SECONDS='180')
        cases = {case['id']: case for case in json.loads(benchmark.DATASET.read_text())['cases']}
        parent = ROOT / 'edh-model-eval' / 'diagnostics'
        parent.mkdir(parents=True, exist_ok=True)
        output = Path(tempfile.mkdtemp(prefix=f'actor-{args.model}.', dir=parent))
        rows = []
        print(f'Diagnostic directory: {output}', flush=True)
        with (output / 'trials.jsonl').open('w') as archive:
            for arm, case in stress_cases(cases, args.model):
                print(f'{args.model}/{arm}: {case["id"]}', flush=True)
                row = run_case(benchmark, arm, case, args.model)
                rows.append(row)
                archive.write(json.dumps(row, ensure_ascii=False) + '\n')
                archive.flush()
        report = summary(args.model, rows)
        path = output / 'report.md'
        path.write_text(report)
        print(report)
        print(f'Report: {path}')
        return 0 if all(row['model_reported'] == args.model for row in rows) else 1
    except KeyboardInterrupt:
        print('Interrupted. Saved diagnostic rows remain available.', file=sys.stderr)
        return 130
    except (OSError, ValueError, KeyError, ImportError, subprocess.SubprocessError) as error:
        print(f'Fatal: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
