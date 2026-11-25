# Experiment 001 — JSON vs JSONL for small local models

**Status:** pilot design; hypothesis unverified. This is a wiki-ready research protocol, not an inference result.

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
