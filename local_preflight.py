#!/usr/bin/env python3
"""Run the public ADR fixtures against local GGUFs and record provenance."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import subprocess
import time
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener

from preflight import CASES, ROOT, live_review, run


MODEL_FILES = {
    'primary': 'Qwen3.8-27B/Qwen3.8-27B-UD-Q5_K_XL.gguf',
    'independent': 'Gemma4-31B/gemma-4-31B-it-qat-UD-Q4_K_XL.gguf',
    'triage': 'Qwen3.5-4B/Qwen3.5-4B-UD-Q5_K_XL.gguf',
}
RUNTIME_OPTIONS = {
    'context_tokens': 8192, 'slots': 1, 'gpu_layers': 99,
    'reasoning_budget': 256, 'timeout_seconds': 180, 'strategy': 'adaptive',
}


def source_revision():
    git = ['git', '-C', str(ROOT)]
    changed = subprocess.check_output(
        [*git, 'status', '--porcelain', '--untracked-files=all', '--',
         'preflight.py', 'local_preflight.py', 'schemas', 'adr'], text=True,
    )
    if changed:
        raise ValueError('Commit the runner, policy, schemas and fixtures before recording evidence')
    return subprocess.check_output([*git, 'rev-parse', 'HEAD'], text=True).strip()


def model_metadata(path):
    with path.open('rb') as model:
        sha256 = hashlib.sha256()
        for block in iter(lambda: model.read(8 * 1024 * 1024), b''):
            sha256.update(block)
    return {
        'file': path.name,
        'quant': re.search(r'UD-Q[0-9]_K_XL', path.name).group(),
        'size_bytes': path.stat().st_size,
        'sha256': sha256.hexdigest(),
    }


@contextmanager
def model_server(binary, path, log):
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    endpoint = f'http://127.0.0.1:{port}'
    options = RUNTIME_OPTIONS
    command = [
        binary, '--host', '127.0.0.1', '--port', str(port), '--model', str(path),
        '--alias', path.stem, '--ctx-size', str(options['context_tokens']),
        '--parallel', str(options['slots']), '--n-gpu-layers', str(options['gpu_layers']),
        '--reasoning-budget', str(options['reasoning_budget']),
    ]
    env = {key: value for key, value in os.environ.items() if not key.startswith('LLAMA_ARG_')}
    with log.open('w') as output:
        process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT, env=env)
    try:
        client = build_opener(ProxyHandler({}))
        deadline = time.monotonic() + 90
        while process.poll() is None and time.monotonic() < deadline:
            try:
                with client.open(endpoint + '/health', timeout=2) as response:
                    if response.status == 200:
                        break
            except (URLError, TimeoutError):
                pass
            time.sleep(1)
        else:
            raise RuntimeError(f'Model server did not become ready: {path.name}. See {log}')
        yield endpoint + '/v1'
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def public_case(case, report, models):
    reviews = []
    for review in report['reviews']:
        role = review['role']
        alias = Path(models[role]['file']).stem
        findings = review.get('findings', [])
        reviews.append({
            'role': role, 'status': review['status'],
            'elapsed_ms': round(review['elapsed_seconds'] * 1000),
            'findings': len(findings),
            'conflicts': sum(f['category'] == 'conflict' for f in findings),
            'model_reported': alias if review.get('model_reported') == alias else None,
            'usage': review.get('usage') or {},
        })
    return {
        'case': case, 'decision': report['decision'], 'execution_authorized': False,
        'policy_sha256': report['policy_sha256'], 'source_sha256': report['source_sha256'],
        'lint_errors': len(report['lint_errors']), 'reviews': reviews,
    }


def run_local(args, output):
    roles = list(MODEL_FILES) if args.triage else ['primary', 'independent']
    paths = {role: args.models_dir / MODEL_FILES[role] for role in roles}
    revision = source_revision()
    binary = args.llama_server
    version = subprocess.check_output([binary, '--version'], text=True, stderr=subprocess.STDOUT, timeout=10)
    version = next(line.removeprefix('version: ').strip() for line in version.splitlines()
                   if line.startswith('version: '))
    print(f'Hashing {len(paths)} GGUF files for the manifest', flush=True)
    models = {role: model_metadata(path) for role, path in paths.items()}
    report = {
        'schema_version': 1, 'mode': 'live-synthetic', 'revision': revision,
        'started_at_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'runtime': {'engine': 'llama.cpp', 'version': version, 'system': platform.system(),
                    'release': platform.mac_ver()[0] or platform.release(),
                    'architecture': platform.machine(), 'python': platform.python_version(),
                    **RUNTIME_OPTIONS},
        'models': models, 'cases': [],
    }
    for key in tuple(os.environ):
        if key.startswith('ADR_'):
            del os.environ[key]
    os.environ['ADR_TIMEOUT_SECONDS'] = str(RUNTIME_OPTIONS['timeout_seconds'])
    os.environ['ADR_ROUTING_STRATEGY'] = RUNTIME_OPTIONS['strategy']
    if args.triage:
        os.environ['ADR_TRIAGE_MODEL'] = paths['triage'].stem

    def review(role, sources, candidate):
        path = paths[role]
        log = output / f'{case}-{role}.log'
        print(f'{case}: running {role} {path.stem}', flush=True)
        with model_server(binary, path, log) as endpoint:
            prefix = f'ADR_{role.upper()}'
            os.environ[prefix + '_URL'] = endpoint
            os.environ[prefix + '_MODEL'] = path.stem
            return live_review(role, sources, candidate)

    for case in args.cases:
        result = run(case, 'live', reviewer=review)
        (output / f'{case}.json').write_text(json.dumps(result, indent=2) + '\n')
        report['cases'].append(public_case(case, result, models))
        print(f'{case}: {result["decision"]}', flush=True)
    (output / 'evidence.json').write_text(json.dumps(report, separators=(',', ':')) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models-dir', type=Path, default=Path.home() / 'models')
    parser.add_argument('--llama-server', default=shutil.which('llama-server'))
    parser.add_argument('--triage', action='store_true', help='Include the optional Qwen 3.5 4B reviewer')
    parser.add_argument('--cases', nargs='+', choices=CASES, default=list(CASES))
    parser.add_argument('--output', type=Path, required=True, help='A directory for this run only')
    args = parser.parse_args()
    if not args.llama_server or len(set(args.cases)) != len(args.cases):
        parser.error('Provide llama-server and use each case at most once')
    try:
        args.output.mkdir(parents=True, exist_ok=True)
        if any(args.output.iterdir()):
            raise ValueError('Choose an empty output directory')
        run_local(args, args.output)
    except (OSError, ValueError, StopIteration, subprocess.SubprocessError) as error:
        parser.exit(1, f'Local preflight setup failed: {error}\n')


if __name__ == '__main__':
    main()
