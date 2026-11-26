#!/usr/bin/env python3
"""Validate and render a developer-submitted synthetic preflight manifest."""

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from local_preflight import CASES, MODEL_FILES, ROOT, RUNTIME_OPTIONS


def require(condition):
    if not condition:
        raise ValueError('Invalid local preflight evidence')


def fields(value, expected):
    require(isinstance(value, dict) and set(value) == set(expected.split()))


def matches(value, pattern):
    return isinstance(value, str) and re.fullmatch(pattern, value) is not None


def count(value, maximum=10**12):
    return type(value) is int and 0 <= value <= maximum


def validate(manifest):
    fields(manifest, 'schema_version mode revision started_at_utc runtime models cases')
    require(type(manifest['schema_version']) is int and manifest['schema_version'] == 1)
    require(manifest['mode'] == 'live-synthetic' and matches(manifest['revision'], r'[0-9a-f]{40}'))
    require(matches(manifest['started_at_utc'], r'[0-9TZ:-]{20}'))
    datetime.strptime(manifest['started_at_utc'], '%Y-%m-%dT%H:%M:%SZ')
    runtime = manifest['runtime']
    fields(runtime, 'engine version system release architecture python ' + ' '.join(RUNTIME_OPTIONS))
    require(runtime['engine'] == 'llama.cpp')
    require(matches(runtime['version'], r'[A-Za-z0-9 .,()+_-]{1,90}'))
    for key in ('system', 'release', 'architecture', 'python'):
        require(matches(runtime[key], r'[A-Za-z0-9.+_-]{1,64}'))
    for key, expected in RUNTIME_OPTIONS.items():
        require(type(runtime[key]) is type(expected) and runtime[key] == expected)

    models = manifest['models']
    require(isinstance(models, dict) and {'primary', 'independent'} <= models.keys() <= MODEL_FILES.keys())
    for role, model in models.items():
        fields(model, 'file quant size_bytes sha256')
        require(model['file'] == Path(MODEL_FILES[role]).name)
        require(matches(model['quant'], r'UD-Q[0-9]_K_XL') and model['quant'] in model['file'])
        require(count(model['size_bytes']) and model['size_bytes'] > 0 and matches(model['sha256'], r'[0-9a-f]{64}'))

    cases = manifest['cases']
    require(isinstance(cases, list) and 0 < len(cases) <= len(CASES))
    names = set()
    for result in cases:
        validate_case(result, models)
        names.add(result['case'])
    require(len(names) == len(cases))


def validate_case(result, models):
    fields(result, 'case decision execution_authorized policy_sha256 source_sha256 lint_errors reviews')
    require(isinstance(result['case'], str) and result['case'] in CASES)
    require(result['decision'] in ('ALLOW', 'REVIEW', 'REJECT') and result['execution_authorized'] is False)
    require(matches(result['policy_sha256'], r'[0-9a-f]{64}') and count(result['lint_errors']))
    sources = result['source_sha256']
    require(isinstance(sources, dict) and {'ADR-0001.md', CASES[result['case']]} <= sources.keys())
    require(all(matches(name, r'ADR-[0-9]{4}\.md') and matches(digest, r'[0-9a-f]{64}')
                for name, digest in sources.items()))
    reviews = result['reviews']
    require(isinstance(reviews, list) and len(reviews) <= len(models))
    roles = set()
    for review in reviews:
        fields(review, 'role status elapsed_ms findings conflicts model_reported usage')
        role = review['role']
        require(isinstance(role, str) and role in models and role not in roles)
        roles.add(role)
        require(review['status'] in ('ok', 'error') and count(review['elapsed_ms']))
        require(count(review['findings'], 20) and count(review['conflicts'], review['findings']))
        require(review['model_reported'] in (None, Path(models[role]['file']).stem))
        usage = review['usage']
        require(isinstance(usage, dict) and usage.keys() <= {'prompt_tokens', 'completion_tokens', 'total_tokens'})
        require(all(count(value) for value in usage.values()))
    require(result['decision'] != 'ALLOW' or ('primary' in roles and all(
        review['status'] == 'ok' and not review['findings'] for review in reviews
    ) and not result['lint_errors']))


def verify_public_sources(manifest):
    revision = manifest['revision']
    git = ['git', '-C', str(ROOT)]
    if subprocess.run([*git, 'cat-file', '-e', revision + '^{commit}'], capture_output=True).returncode:
        subprocess.run([*git, 'fetch', '--depth=1', '--no-tags', 'origin', revision], check=True, timeout=30)

    def verify(path, expected):
        blob = subprocess.check_output([*git, 'show', f'{revision}:{path}'], timeout=15)
        require(hashlib.sha256(blob).hexdigest() == expected)

    for result in manifest['cases']:
        verify('preflight.py', result['policy_sha256'])
        for name, digest in result['source_sha256'].items():
            directory = 'proposed' if name == CASES[result['case']] else 'accepted'
            verify(f'adr/{directory}/{name}', digest)


def markdown(manifest):
    runtime = manifest['runtime']
    lines = [
        '# Developer-run ADR preflight', '',
        f"Source revision `{manifest['revision']}` · `{manifest['started_at_utc']}`", '',
        f"llama.cpp `{runtime['version']}` · Python `{runtime['python']}` · "
        f"`{runtime['system']} {runtime['release']} {runtime['architecture']}`", '',
        '| Role | GGUF | Quant | SHA-256 |', '| --- | --- | --- | --- |',
    ]
    for role, model in manifest['models'].items():
        lines.append(f"| {role} | `{model['file']}` | {model['quant']} | `{model['sha256']}` |")
    lines += ['', '| Case | Decision | Review status | Findings | Conflicts |', '| --- | --- | --- | ---: | ---: |']
    for result in manifest['cases']:
        reviews = result['reviews']
        statuses = ', '.join(f"{r['role']} {r['status']}" for r in reviews) or 'No inference'
        lines.append(f"| {result['case']} | {result['decision']} | {statuses} | "
                     f"{sum(r['findings'] for r in reviews)} | {sum(r['conflicts'] for r in reviews)} |")
    lines += ['', 'The workflow verified the submitted source hashes. Runtime and model provenance were reported by the developer.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, help='Read a file instead of ADR_LOCAL_EVIDENCE')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        payload = args.input.read_text() if args.input else os.environ.get('ADR_LOCAL_EVIDENCE', '')
        require(0 < len(payload.encode()) <= 24_000)
        manifest = json.loads(payload)
        validate(manifest)
        verify_public_sources(manifest)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(1, f'Local preflight evidence rejected ({type(error).__name__})\n')
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'evidence.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (args.output / 'summary.md').write_text(markdown(manifest))


if __name__ == '__main__':
    main()
