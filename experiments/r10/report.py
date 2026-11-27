#!/usr/bin/env python3
"""Generate public-safe R10 report files and Actions job summary from observed trials."""
import argparse, hashlib, json, math, os, pathlib, statistics
from html import escape
import context_abc

KEYS=("trials","valid","exact","tp","fp","fn")
DATASET="5231e42696e265c6b067ef3c37746c73732286473a7ba192fd8e59974026ad92"
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def median(v): return statistics.median(v) if v else None
def load(root):
    if sha(root/"dataset.json")!=DATASET: raise ValueError("dataset mismatch")
    cases={x["id"]:x for x in json.loads((root/"dataset.json").read_text())["cases"]}
    rows=[json.loads(x) for x in (root/"trials.jsonl").read_text().splitlines()]
    report=json.loads((root/"comparison.json").read_text())
    meta=json.loads((root/"provenance.json").read_text())
    suite=meta["suite"]; repeats=meta["repeats"]
    if suite not in ("original-six","adr-only") or repeats not in (1,2,3): raise ValueError("invalid protocol")
    protocol=meta.get("protocol","format-only")
    arms=context_abc.PROTOCOL_ARMS[protocol]
    is_abc=protocol=="context-abc"
    if tuple(meta["arms"])!=arms or report.get("protocol","format-only")!=protocol:
        raise ValueError("inconsistent protocol")
    ids={k for k in cases if suite=="original-six" or k.startswith("adr-")}
    expected={(k,a,r) for k in ids for a in arms for r in range(repeats)}
    seen=set()
    for row in rows:
        k=(row["case"],row["arm"],row["repeat"])
        if k not in expected or k in seen: raise ValueError("unexpected/duplicate trial")
        seen.add(k)
        case=cases[row["case"]]
        if is_abc:
            records=context_abc.visible_records(case,row["arm"])
            canonical=json.dumps(records,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
            if row["records_sha256"]!=hashlib.sha256(canonical).hexdigest():
                raise ValueError("visible record set mismatch")
            assessments=row["assessments"]
            if row["valid"]!=(assessments is not None):
                raise ValueError("assessment validity mismatch")
            if assessments is not None:
                normalized, discarded=context_abc.normalize({"assessments":assessments},records)
                if discarded or normalized!=assessments:
                    raise ValueError("unexpected stored assessment")
            if type(row["invalid_constraint_refs"]) is not int or row["invalid_constraint_refs"]<0:
                raise ValueError("invalid reference count")
            metrics=context_abc.score(case,row["arm"],assessments)
            if any(row[key]!=value for key,value in metrics.items()):
                raise ValueError("candidate score mismatch")
        else:
            g=set(map(tuple,case["expected"])); f=set(map(tuple,row["found"]))
            if set(map(tuple,row["gold"]))!=g or (row["tp"],row["fp"],row["fn"],row["exact"])!=(len(f&g),len(f-g),len(g-f),bool(row["valid"] and f==g)): raise ValueError("score mismatch")
        if not math.isfinite(row["elapsed_seconds"]) or row["elapsed_seconds"]<0: raise ValueError("invalid timing")
    for a in arms:
        rr=[r for r in rows if r["arm"]==a]; s=report["arms"][a]
        computed={"trials":len(rr),**{k:sum(r[k] for r in rr) for k in KEYS[1:]},"median_wall_seconds":median([r["elapsed_seconds"] for r in rr]),"median_prompt_tokens":median([r["usage"]["prompt_tokens"] for r in rr if "prompt_tokens" in r["usage"]]),"median_total_tokens":median([r["usage"]["total_tokens"] for r in rr if "total_tokens" in r["usage"]])}
        if is_abc:
            computed.update(context_abc.summarize(rr,a))
        if any(s[k]!=v for k,v in computed.items()): raise ValueError("summary mismatch")
    if report["trials"]!=len(rows) or report["cases"]!=len(ids): raise ValueError("summary coverage mismatch")
    complete=seen==expected and all(r["valid"] for r in rows)
    return report,meta,complete,len(expected)
def plot(path,report,baseline,arms,key,title,seconds=False):
    def t(x,y,s,size=16,weight=400):
        return f'<text x="{x}" y="{y}" font-family="Arial,sans-serif" font-size="{size}" font-weight="{weight}" fill="#23364a">{escape(str(s))}</text>'
    vals=[v for a in arms for v in (report["arms"][a][key],baseline["arms"][a][key] if baseline else None) if v is not None]
    mx=max([1]+vals)
    b=t(25,35,title,24,700)+t(25,60,"R10 synthetic development corpus - feasibility only",15)
    b+='<rect x="25" y="75" width="16" height="15" fill="#0d9488"/>'+t(49,88,"Current run")
    if baseline: b+='<rect x="235" y="75" width="16" height="15" fill="#526d91"/>'+t(260,88,"Original Mac baseline")
    for i,a in enumerate(arms):
        y=115+i*86
        b+=t(25,y+25,a.upper(),16,700)
        for j,(s,c) in enumerate([(report,"#0d9488")]+([(baseline,"#526d91")] if baseline else [])):
            v=s["arms"][a][key]; yy=y+j*28
            if v is None: b+=t(155,yy+17,"N/A"); continue
            w=v/mx*530
            b+=f'<rect x="155" y="{yy}" width="{w:.2f}" height="21" rx="3" fill="{c}"/>'+t(164+w,yy+17,f"{v:.3f} s" if seconds else v)
    b+=t(25,388,"No production or statistical superiority claim.",15)
    path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="850" height="410" viewBox="0 0 850 410"><title>'+escape(title)+'</title><rect width="850" height="410" rx="10" fill="#ffffff"/>'+b+'</svg>\n')
def main():
    p=argparse.ArgumentParser(); p.add_argument("root",type=pathlib.Path); p.add_argument("--mode",choices=("github-free","github-paid","external-api","local"),required=True); a=p.parse_args()
    root=a.root
    if not all((root/n).is_file() for n in ("dataset.json","trials.jsonl","comparison.json","provenance.json")):
        root.mkdir(parents=True,exist_ok=True); md="# R10 benchmark — incomplete evidence\n\nRequired evidence files missing; no metrics asserted.\n"
        (root/"report.md").write_text(md)
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write(md)
        return 2
    report,meta,complete,expected=load(root)
    protocol=meta.get("protocol","format-only")
    arms=context_abc.PROTOCOL_ARMS[protocol]
    baseline=json.loads(pathlib.Path(__file__).with_name("original-comparison.json").read_text()) if protocol=="format-only" and meta["suite"]=="original-six" and meta["repeats"]==1 else None
    status="COMPLETE — FEASIBILITY ONLY" if complete else "INCOMPLETE / INVALID — NOT A PASS"
    run=os.environ.get("GITHUB_RUN_ID","local")
    if not run.isdigit():run="local"
    md=f"# R10 benchmark — {status}\n\nRun: {run} · Mode: {a.mode} · Protocol: {protocol} · Suite: {meta['suite']} · Repeats: {meta['repeats']}\n\nObserved calls: {report['trials']}/{expected}.\n\n| Arm | Calls | Valid | Exact | TP | FP | FN | Median seconds | Prompt tokens (median) | Total tokens (median) |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n"
    for arm in arms:
        s=report["arms"][arm]
        def fmt(k): return "N/A" if s[k] is None else f"{s[k]:.3f}" if k=="median_wall_seconds" else str(s[k])
        md+="| "+arm.upper()+" | "+" | ".join(fmt(k) for k in KEYS+("median_wall_seconds","median_prompt_tokens","median_total_tokens"))+" |\n"
    if protocol=="context-abc":
        md+="\nA: candidate only. B: candidate and Markdown constraints. C: the same records in JSONL.\n"
        md+="\n| Arm | Answered candidates / total | Abstentions | Positive abstentions | Constraint reference TP / FP / FN | Discarded references |\n| --- | ---: | ---: | ---: | ---: | ---: |\n"
        for arm in arms:
            s=report["arms"][arm]
            refs=s["constraint_refs"]
            counts=" / ".join(str(refs[key]) for key in ("tp","fp","fn")) if refs is not None else "N/A"
            md+=f"| {arm} | {s['answered_candidates']} / {s['candidates']} | {s['abstentions']} | {s['positive_abstentions']} | {counts} | {s['invalid_constraint_refs']} |\n"
        md+="\nThe primary scores count candidate decisions. Exact match requires a resolved answer for every candidate. Missed positives include positive abstentions, which are also shown separately. Constraint references are a secondary measure for B and C.\n"
    if baseline:
        md+="\n## Original Mac baseline comparison\n\n| Format | Exact (Mac / current) | FP (Mac / current) | Median seconds (Mac / current) |\n|---|---:|---:|---:|\n"
        for arm in arms:
            m=baseline["arms"][arm]; s=report["arms"][arm]; v=s["median_wall_seconds"]; cur="N/A" if v is None else f"{v:.3f}"
            md+=f"| {arm.upper()} | {m['exact']} / {s['exact']} | {m['fp']} / {s['fp']} | {m['median_wall_seconds']:.3f} / {cur} |\n"
    md+="\nDevelopment cases, not an independent holdout. Runtime/provider differences may affect results. No production approval or measured cost saving.\n\n[Permanent first hosted evidence](https://github.com/edh-project/edh-adr-preflight/tree/main/docs/research/r10/evidence/first-hosted). Download the run artifact for SVG charts, trial rows and provenance.\n"
    for name,key,title,seconds in (("exact-match","exact","Exact matches",False),("false-positives","fp","False-positive findings",False),("median-latency","median_wall_seconds","Median request wall time (s)",True)):
        plot(root/(name+".svg"),report,baseline,arms,key,title,seconds)
    (root/"report.md").write_text(md+"\n"+"\n\n".join(f"![{n}]({n}.svg)" for n in ("exact-match","false-positives","median-latency"))+"\n")
    files=sorted(p for p in root.iterdir() if p.is_file() and p.name!="SHA256SUMS")
    (root/"SHA256SUMS").write_text("".join(f"{sha(p)}  {p.name}\n" for p in files))
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write(md)
    return 0 if complete else 2
if __name__=="__main__": raise SystemExit(main())
