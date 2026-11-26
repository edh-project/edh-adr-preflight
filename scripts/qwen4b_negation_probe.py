#!/usr/bin/env python3
"""Compare the original and a clarified review prompt on six synthetic ADR cases."""

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from urllib.request import ProxyHandler, build_opener


PAIRS = {
    'original': (
        'Coding agent returns a patch without production credentials.',
        'Coding agent returns a patch with production credentials.',
    ),
    'receives': (
        'The coding agent does not receive production credentials.',
        'The coding agent receives production credentials.',
    ),
    'issued': (
        'Production credentials will not be issued to the coding agent.',
        'Production credentials will be issued to the coding agent.',
    ),
}
CLARIFICATION = (
    'Compare the actions, actors and polarity of the statements. If a candidate '
    'explicitly says that an action is not performed, that statement is compatible '
    'with a rule that prohibits the same action. Shared words alone do not establish '
    'a violation. Report a pair only if the candidate explicitly performs or permits '
    'an action that the constraint prohibits or excludes. '
)


def load_file(name, path):
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Cannot load {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def synthetic_cases(benchmark):
    dataset = json.loads(benchmark.DATASET.read_text())['cases']
    clean = next(case for case in dataset if case['id'] == 'adr-clean')
    if clean['expected'] or len([r for r in clean['records'] if r['id'] == 'P1']) != 1:
        raise ValueError('Unexpected clean ADR in the pinned benchmark')
    for pair, statements in PAIRS.items():
        for variant, statement in zip(('compliant', 'violating'), statements):
            yield {
                'id': f'{pair}-{variant}',
                'records': [dict(record, text=statement) if record['id'] == 'P1' else record
                            for record in clean['records']],
                'expected': [] if variant == 'compliant' else [['P1', 'C1']],
            }


def report(rows, metadata):
    lines = [
        '# Qwen 4B explicit negation probe', '',
        f'Benchmark revision: {metadata["benchmark_revision"]}. Model: {metadata["model"]}.',
        '',
        '| Prompt | Valid | Exact | FP | FN | Correct matched pairs |',
        '| --- | ---: | ---: | ---: | ---: | ---: |',
    ]
    for prompt in ('original', 'clarified'):
        subset = [row for row in rows if row['prompt'] == prompt]
        by_case = {row['case']: row for row in subset}
        paired = sum(all(by_case[f'{pair}-{variant}']['exact'] for variant in ('compliant', 'violating'))
                     for pair in PAIRS)
        lines.append(f"| {prompt} | {sum(r['valid'] for r in subset)}/6 | "
                     f"{sum(r['exact'] for r in subset)}/6 | {sum(r['fp'] for r in subset)} | "
                     f"{sum(r['fn'] for r in subset)} | {paired}/3 |")
    lines += ['', '| Pair | Case | Prompt | Valid | Expected | Found | Error |',
              '| --- | --- | --- | --- | --- | --- | --- |']
    for row in rows:
        pair, variant = row['case'].split('-', 1)
        expected = ', '.join('/'.join(x) for x in row['gold']) or '—'
        found = ', '.join('/'.join(x) for x in row['found']) or '—'
        lines.append(f"| {pair} | {variant} | {row['prompt']} | {row['valid']} | "
                     f"{expected} | {found} | {row.get('error_type', '—')} |")
    lines += ['', 'A matched pair is correct when both responses pass validation '
              'and match their labels. This is a targeted regression probe on one synthetic rule. '
              'The original prompt already includes the findings-only output instructions. '
              'This probe does not compare JSON with JSONL.', '']
    return '\n'.join(lines)


def run(diagnostic, args):
    pilot = diagnostic.pilot
    if 'schema-findings' not in diagnostic.CONDITIONS:
        raise RuntimeError('Use the updated diagnostic with --condition schema-findings')
    model = pilot.prepare_model(args.model_dir or pilot.DEFAULT_MODEL_DIR, offline=True)
    work = args.work_dir or pilot.DEFAULT_WORK_DIR
    checkout = pilot.prepare_checkout(work, offline=True)
    benchmark_path = checkout / 'benchmark_jsonl.py'
    benchmark = load_file('edh_negation_benchmark', benchmark_path)
    if benchmark.PROMPT.count('Record schema:') != 1:
        raise ValueError('Unexpected prompt in the pinned benchmark')
    variants = {
        'original': benchmark,
        'clarified': SimpleNamespace(**vars(benchmark)),
    }
    variants['clarified'].PROMPT = benchmark.PROMPT.replace('Record schema:', CLARIFICATION + 'Record schema:')
    cases = list(synthetic_cases(benchmark))
    random.Random(42).shuffle(cases)

    binary = pilot.executable('llama-server')
    version = subprocess.check_output([binary, '--version'], text=True, stderr=subprocess.STDOUT, timeout=10)
    parent = work / 'diagnostics'
    parent.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix='negation-', dir=parent))
    print(f'Diagnostic directory: {output}', flush=True)
    metadata = {
        'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'benchmark_revision': pilot.PILOT_REVISION, 'model': pilot.MODEL_FILE,
        'model_sha256': pilot.MODEL_SHA256, 'server_version': version.strip(),
        'server_flags': pilot.SERVER_FLAGS, 'max_tokens': pilot.MAX_TOKENS,
        'condition': 'schema-findings', 'temperature': 0, 'case_order_seed': 42,
        'prompt_clarification': CLARIFICATION,
        'benchmark_sha256': pilot.sha256(benchmark_path),
        'source_dataset_sha256': pilot.sha256(benchmark.DATASET),
        'diagnostic_sha256': pilot.sha256(args.diagnostic),
        'probe_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    (output / 'provenance.json').write_text(json.dumps(metadata, indent=2) + '\n')
    (output / 'cases.json').write_text(json.dumps(cases, indent=2) + '\n')
    opener = build_opener(ProxyHandler({}), benchmark.NoRedirect())
    rows = []
    with pilot.start_server(binary, model, output / 'llama-server.log') as endpoint, \
            (output / 'trials.jsonl').open('w') as archive:
        for index, case in enumerate(cases):
            order = list(variants)
            if index % 2:
                order.reverse()
            for prompt in order:
                print(f'{prompt}: {case["id"]}', flush=True)
                row = diagnostic.one_request(variants[prompt], opener, endpoint, 'schema-findings',
                                             case, 'json', 0, pilot.MAX_TOKENS)
                row['prompt'] = prompt
                rows.append(row)
                archive.write(json.dumps(row, ensure_ascii=False) + '\n')
                archive.flush()
    summary = report(rows, metadata)
    path = output / 'report.md'
    path.write_text(summary)
    print(summary)
    print(f'Report: {path}')
    return 0 if all(row['api_response'] for row in rows) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('diagnostic', type=Path, help='Path to the existing diagnostic Python script')
    parser.add_argument('--model-dir', type=Path)
    parser.add_argument('--work-dir', type=Path)
    args = parser.parse_args()
    args.diagnostic = args.diagnostic.expanduser().resolve()
    if args.model_dir is not None:
        args.model_dir = args.model_dir.expanduser().resolve()
    if args.work_dir is not None:
        args.work_dir = args.work_dir.expanduser().resolve()
    try:
        return run(load_file('edh_negation_diagnostic', args.diagnostic), args)
    except KeyboardInterrupt:
        print('Interrupted. Saved trial rows remain on disk.', file=sys.stderr)
        return 130
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f'Fatal: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
