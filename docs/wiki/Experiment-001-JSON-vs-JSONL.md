# Experiment 001 — JSON vs JSONL for small local models

**Status:** fixture CI passed; live-model hypothesis remains unverified. This is a research protocol and implementation checkpoint, not an inference result.

## Current state — 2026-11-25

The benchmark implementation is in [draft PR #2](https://github.com/edh-project/edh-adr-preflight/pull/2), with the original experiment commit [2c7d926](https://github.com/edh-project/edh-adr-preflight/commit/2c7d926be487bcbd4fe16c7afae32015981832e4). The main branch remains unchanged by this experiment.

| Component | Status / evidence |
|---|---|
| Deterministic PR rejection | [PR #1 structural check](https://github.com/edh-project/edh-adr-preflight/actions/runs/45569140916): expected failure, independent of inference |
| Existing BYOI adapter | [Regression CI](https://github.com/edh-project/edh-adr-preflight/actions/runs/45570202159): passed |
| Paired benchmark harness | [Benchmark CI](https://github.com/edh-project/edh-adr-preflight/actions/runs/45571575915): passed |
| Unit tests | 24/24 passed in benchmark job logs |
| Fixture experiment | Six cases × three repetitions × two arms = 36 oracle-stub trials; harness passed |
| Evidence | [Fixture artifact](https://github.com/edh-project/edh-adr-preflight/actions/runs/45571575915/artifacts/15002341583) uploaded; ZIP contains the intended trial, comparison and summary outputs |
| Live inference | Skipped intentionally on PR; zero measured model requests in this CI run |
| Verdict | HARNESS_ONLY_NOT_MEASURED |

The successful run confirms harness execution, not model performance. There is no measured latency or token advantage, and neither format has demonstrated superiority. The benchmark is separate from the admission policy; it never authorizes execution.

## Next steps and acceptance gates

- [ ] **P0 — Local execution:** check out PR #2 on a trusted workstation; verify the served model ID and endpoint with /v1/models. Choose a small model (initial candidate: Qwen 4B, exact build and quantization to be recorded). Record hardware, server version, context length, inference settings and cache/warm-up state. Do not attach a personal runner to the public repository.
- [ ] **P0 — First measured pair:** execute three repetitions for one model (36 actual requests), using identical settings in both arms. Preserve trials.jsonl, comparison.json and summary.md, including errors, invalid outputs and unavailable token counts. Check that all 18 pairs are represented; do not substitute fixture results for live trials.
- [ ] **P0 — Review evidence:** compare exact matches, valid responses, TP/FP/FN, precision/recall and paired latency/token deltas; examine invalid or truncated outputs and verify findings against the labeled records. Apply the prespecified verdict without changing the rule after viewing results. Document run configuration and limitations.
- [ ] **P1 — Replicate:** repeat on a second small model, with its own endpoint, model ID, output directory and report. Do not pool model results. Optionally use a larger model as a reference, clearly labeled as such.
- [ ] **P1 — PR review and hosted reproducibility:** review tests and security boundaries, then merge only when approved. The manually dispatched live GitHub Action is intentionally main-only; until merge, use the local CLI from the experiment branch. Hosted execution requires a reachable HTTPS inference service configured by the operator, not workstation localhost.
- [ ] **P2 — Isolate the effect:** add a 2×2 ablation (JSON/JSONL input crossed with JSON/JSONL output), a schema-constrained JSON baseline, and a larger independently labeled held-out ADR/code corpus. Keep sample selection and evaluation rules fixed before runs.
- [ ] **P2 — Strengthen measurement:** repeat on independent samples, quantify uncertainty and caching/order effects, then study streaming/time-to-first-finding separately. Decide whether to integrate the winning format into ADR preflight only after reviewing evidence; do not change runtime admission semantics based on this pilot.

**Exit criterion for the first live milestone:** a reproducible evidence bundle for at least one small model, a recorded configuration, complete pair accounting and a justified verdict (including inconclusive or regression). No requirement that JSONL wins.

## Research question

Does representing the same ADR/code evidence and findings as JSON Lines improve validation reliability or resource efficiency on small self-hosted models compared with ordinary JSON? Motivation: observed benefits on larger Qwen models; transfer to small models is unknown.

## Experimental design

| Factor | Baseline | Experimental |
|---|---|---|
| Input | JSON array of addressable records | JSONL, one identical record per line |
| Output | JSON array of finding records + completion | JSONL finding records + completion |
| Transport | OpenAI-compatible chat completions, non-streaming | Same |
| Model | Same exact served alias, quantization, server and settings | Same |
| Decoding | temperature 0, same max tokens; no grammar/schema forcing | Same |
| Evidence | same record IDs, text, gold pairs, validation rules | Same |

The experiment changes both input and output encoding as one intervention. It does not isolate which causes a difference; a later 2×2 design should separate them. It is not a comparison against the existing schema-constrained production-shaped adapter. No claim about streaming or time to first finding follows from this non-streaming pilot.

The six synthetic cases cover clean and conflicting ADR decisions and tiny code snippets (three negative and three positive cases). Gold labels are explicit pairs of candidate and constraint IDs, held outside model prompts. Record IDs and text are identical across arms. The cases are curated and small; generalization to full ADRs, real diffs and larger corpora requires a separate dataset. The benchmark does not execute code or grant admission.

## Protocol

1. Choose one small model and record exact GGUF filename/quantization, llama.cpp build, hardware, context settings and actual served model alias in a separate run note. Repeat independently for each model (e.g. Qwen 4B then a second small model). Do not pool different models.
2. Start one server; avoid concurrent inference. Warm up separately if desired, identically across experiments; note cache state. The harness uses a fixed shuffled case order and alternates JSON/JSONL first to reduce order bias. It does not control provider caching or temperature-zero nondeterminism.
3. Run at least three repetitions (36 requests per model; five gives 60). The same output limit applies to both arms. Record timeouts, invalid responses and missing usage; do not discard failures from accuracy.
4. Compare exact case match, schema/reference/completion validity, TP/FP/FN, precision and recall; compare paired median latency and provider-reported token deltas only where both outputs are valid and metrics exist. Record bytes and hashes as diagnostic evidence, not substitute token counts.
5. Missing completion, unknown IDs, duplicate findings or non-stop finish invalidate the response. Invalid trials cannot count as exact matches; gold violations are counted as missed. No automatic admission is possible.

## Prespecified interpretation

Fixture runs always report HARNESS_ONLY_NOT_MEASURED: the stub is given gold labels to test the pipeline, not model ability. Timing and token metrics are absent, not zero. A live run is inconclusive by default. With at least three repetitions and all paired outputs valid, a JSONL quality regression is flagged if exact matches decrease or FP/FN increase. Otherwise JSONL is marked promising (not proven) only if exact matches do not decrease, FP/FN do not increase, and median latency or total tokens improves on all measured pairs. No statistical significance or general superiority is claimed. The pilot must be repeated on a larger independent corpus before an adoption decision.

## Reproduce

From the repository root on a trusted local host:

```sh
python3 benchmark_jsonl.py --mode fixture --repeats 3 --output reports/jsonl-fixture
```

```sh
export ADR_PRIMARY_URL=http://127.0.0.1:8080/v1
export ADR_PRIMARY_MODEL='REPLACE_WITH_SERVED_ALIAS'
export ADR_TIMEOUT_SECONDS=180
python3 benchmark_jsonl.py --mode live --repeats 3 --output reports/jsonl-qwen
```

Use any configured loopback address and port (including 8081 for a second model). For remote inference, use ADR_ENDPOINT_POLICY=https-only with an operator-configured HTTPS endpoint. Set ADR_PRIMARY_API_KEY securely if required, never commit it. The GitHub-hosted manual workflow uses repository Variables and Secrets on main only. PRs run both arms with an oracle stub and no secrets or external inference. Never connect a personal self-hosted runner to the public repository.

## Evidence artifacts

- trials.jsonl: one record per arm/case/repetition, gold and validated finding pairs, finish status, validity, score, provider token usage when available, elapsed time, input/output bytes and hashes. Raw model text is deliberately not published.
- comparison.json: aggregate quality, paired resource deltas, dataset/benchmark hashes, descriptive verdict.
- summary.md: human-readable comparison and explicit limitations.

Results describe a format experiment, not architectural approval. Next steps: actual small-model measurements, 2×2 input/output ablation, larger held-out corpus, streaming and constrained-decoding study.
