#!/usr/bin/env python3
"""Write a human-readable GitHub Actions summary from JSON evidence."""
import argparse
import json
from pathlib import Path

EXPECTED = {'ADR-0002.md': 'ALLOW', 'ADR-0003.md': 'REVIEW', 'ADR-0004.md': 'REJECT'}

def cell(value):
    text=str(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('|', '&#124;').replace('\n', ' ').replace('\r',' ')
    # Model-provided strings are data, not Markdown links, images or mentions.
    import re
    return re.sub(r'([\\\[\]()`*_!@])',r'\\\1',text)

def render(paths):
    reports = [json.loads(p.read_text()) for p in paths]
    lines = ['# ADR preflight — validation evidence', '',
             'ALLOW is a preflight result, not execution authorization.', '',
             '| ADR | Mode | Decision | Expected fixture | Fixture match |', '|---|---|---|---|---|']
    for r in reports:
        expected = EXPECTED.get(r['candidate'], 'N/A') if r['mode']=='fixture' else 'N/A'
        match = ('PASS' if r['decision']==expected else 'FAIL') if expected!='N/A' else 'N/A'
        lines.append('| ' + ' | '.join(map(cell, (r['candidate'],r['mode'],r['decision'],expected,match))) + ' |')
    fixtures = [r for r in reports if r['mode']=='fixture']
    if fixtures:
        passed = sum(EXPECTED.get(r['candidate'])==r['decision'] for r in fixtures)
        lines += ['', f'**Fixture cases matching expectation: {passed}/{len(fixtures)}.** Synthetic responses only; no inference quality claim.']
    for r in reports:
        lines += ['', '## '+cell(r['candidate']), '', '- Execution authorized: **'+str(r['execution_authorized']).lower()+'**', '- Routing: '+cell(r.get('routing_reason','not invoked'))]
        for err in r['lint_errors']:
            lines.append('- Lint: '+cell(err))
        for rev in r['reviews']:
            lines += ['', '### '+cell(rev['role'])+' — '+cell(rev['status']), '- Requested model: '+cell(rev.get('model_requested','N/A')), '- Reported model: '+cell(rev.get('model_reported','N/A')), '- Elapsed seconds: '+cell(rev.get('elapsed_seconds','N/A')), '- Tokens (provider usage): '+cell(rev.get('usage','N/A'))]
            if rev.get('error_type'): lines.append('- Error: '+cell(rev['error_type']))
            for f in rev.get('findings',[]):
                lines += ['- '+cell(f['severity']+' / '+f['category']+' / '+f['source']), '  - Evidence: '+cell(f['quote']), '  - Reason: '+cell(f['reason'])]
    return '\n'.join(lines)+'\n'

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('paths',nargs='+',type=Path);args=ap.parse_args();print(render(args.paths),end='')
