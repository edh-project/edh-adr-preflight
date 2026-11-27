# R10-E01 — Reproducible inference benchmark

Development feasibility only. [R10 research](../../docs/research/r10/README.md) · [Manual workflow](../../.github/workflows/r10-benchmark.yml)

Default: public GitHub-hosted Ubuntu, exact frozen six-case dataset (three ADR and three code cases), three formats, one repeat = 18 calls. ADR-only selects nine calls. The original probe and aggregate baseline are preserved unchanged for provenance. The adapted runner uses the same prompt, records, randomized schedule and scoring; hosted runtime differs from the original Mac build. [First hosted run evidence](../../docs/research/r10/evidence/first-hosted/README.md) is published.

## Manual dispatch

Select **format-only** (default) to reproduce the existing Markdown / JSON / JSONL comparison on identical records. Select **context-abc** to use the following pilot protocol:

| Arm | Records sent to the model | Input format |
| --- | --- | --- |
| A | Candidate records | Markdown |
| B | Candidate and accepted constraint records | Markdown |
| C | The same records as B | JSONL |

The same model, prompt, response schema and decoding settings apply to all three arms. The runner retains gold labels locally. Each model response labels every candidate as a violation, compliant, or unresolved due to insufficient context. Primary metrics compare those decisions with gold at the candidate level. Exact match requires every candidate to be resolved correctly. Unresolved positives are included in end-to-end FN and also reported as positive abstentions. The report shows coverage alongside TP/FP/FN. Constraint reference accuracy is reported for B and C. Guessed or duplicate references are counted and discarded separately from the primary decision.

One repeat is 18 inference calls for `original-six` or nine for `adr-only` in either protocol. The existing corpus is a development fixture. The A/B/C results require their own comparison because the output schema and scoring unit differ from the historic format-only run.

Free mode needs no secrets or model download credentials. The workflow downloads the exact locally verified Unsloth GGUF revision and pinned llama.cpp Linux release, checks SHA-256, starts loopback inference and terminates with the job. No permanent hosting or model weights in Git.

Paid mode requires explicit authorization, a configured organization-approved **GitHub-hosted** x64 larger runner label in repository variables R10_PAID_CPU_RUNNER or R10_PAID_GPU_RUNNER, and the r10-paid environment. Never configure self-hosted labels. CUDA 12.8 support and entitlement must be verified before dispatch. Use environment protection and spending limits.

External mode requires explicit authorization plus an approved GitHub environment named r10-external-1 through r10-external-4, r10-openai or r10-anthropic. Set environment variables R10_EXTERNAL_APPROVED=true, R10_URL (HTTPS API base, no credentials), R10_MODEL, and environment secret R10_API_KEY when needed. OpenAI-compatible profiles expect /chat/completions appended to base (e.g. https://api.openai.com/v1); Anthropic expects /messages appended to https://api.anthropic.com/v1. External profiles support compatible structured-output APIs only; provider-specific API capabilities must be tested. No organization names, addresses, keys or assumptions about access are embedded. Native Gemini/Bedrock and proprietary adapters are not implemented; compatible gateways may be configured only with approval. No external calls or paid runs authorized by publication.

Only frozen public synthetic records are sent; no gold labels, private ADRs, arbitrary inputs, redirects or proxy use. Public artifacts contain synthetic corpus, minimized findings, metrics and provenance; no raw external response bodies or API keys. Model identifiers in responses may be visible; approve public disclosure before enabling a profile. Do not use a confidential endpoint configuration or production credentials in a public repo.

## Metrics and limits

Exact match, valid response, TP/FP/FN, wall latency, token usage and requested settings. A run with invalid/missing responses fails rather than claiming a pass. External settings differ where local-only options are unavailable. Native schema support varies, no silent downgrade. No independent holdout, no energy measurements, no production approval, no cost savings claims. Original script and baseline are historical evidence, not a claim of identical runtime reproduction.

Local execution with an already running loopback model:
```sh
python3 experiments/r10/runner.py --output reports/r10-local --suite original-six --repeats 1
```
Use a new output directory for each run. 

Pass `--protocol context-abc` to run the context ablation on the same loopback model. The output keeps the protocol, visible record hashes and scoring code hash in its evidence files.

## Automated reporting

Each manual execution generates a Markdown Job Summary, `report.md`, three SVG charts and `SHA256SUMS` alongside the observed trial data. Metrics are checked against the frozen corpus and recomputed before reporting; invalid or incomplete runs remain failures. Original Mac baseline is shown only for the matching six-case, one-repeat protocol. Artifacts expire after seven days; selected reviewed synthetic evidence is preserved separately in the research directory. No automatic commits or write permissions.

Future runs record selected CPU model, logical CPU count, total memory and runner image metadata where available; historical runs lack these details. These are environment descriptors, not measured peak utilization.
