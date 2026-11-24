#!/usr/bin/env python3
"""Trusted-base structural PR review, no model calls or execution permissions."""
import argparse
import json
import re
import subprocess
from pathlib import Path
from preflight import lint, digest


def git(*args):
    return subprocess.check_output(['git', *args], text=True, timeout=30)


def check(base, head):
    for sha in (base, head):
        if not re.fullmatch(r'[0-9a-f]{40}', sha):
            raise ValueError('Expected immutable commit SHA')
    paths = git('diff', '--name-only', '--no-renames', '-z', base, head, '--', 'adr/').split('\0')
    results = []
    accepted = [p for p in git('ls-tree', '-r', '--name-only', base, '--', 'adr/accepted/').splitlines() if re.fullmatch(r'adr/accepted/ADR-\d{4}\.md',p)]
    baseline = {p: git('show', f'{base}:{p}') for p in accepted}
    baseline_errors = [p+': '+e for p,t in baseline.items() for e in lint(t,'Accepted')]
    if not baseline: baseline_errors.append('Missing trusted accepted baseline')
    for p in filter(None,paths):
        errors = list(baseline_errors)
        text = ''
        if not re.fullmatch(r'adr/proposed/ADR-\d{4}\.md',p):
            errors.append('Changes outside proposed ADR namespace require separate review')
        else:
            try:
                size=int(git('cat-file','-s',f'{head}:{p}'))
                if size>40000: errors.append('ADR exceeds size limit')
                else: text=git('show',f'{head}:{p}'); errors.extend(lint(text,'Proposed'))
            except subprocess.CalledProcessError: errors.append('ADR deletion or inaccessible object requires review')
        results.append({'path':p,'sha256':digest(text),'decision':'REJECT' if errors else 'REVIEW','lint_errors':errors,'semantic_review':'not run on hosted PR runner','execution_authorized':False})
    return {'base':base,'head':head,'mode':'pr-structural-only','trusted_baseline_sha256':{p:digest(t) for p,t in baseline.items()},'results':results,'execution_authorized':False}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base',required=True);ap.add_argument('--head',required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    report=check(a.base,a.head);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print('# PR ADR structural check\n\nNo semantic review or execution authorization.\n\n| ADR | Decision |\n|---|---|')
    for r in report['results']:
        safe=r['path'].replace('|','&#124;').replace('<','&lt;').replace('>','&gt;').replace('\n',' ')
        print(f"| {safe} | {r['decision']} |")
    return 3 if any(r['decision']=='REJECT' for r in report['results']) else 0

if __name__=='__main__': raise SystemExit(main())
