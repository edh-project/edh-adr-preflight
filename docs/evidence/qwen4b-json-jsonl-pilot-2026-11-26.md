# Qwen 4B JSON and JSONL pilot

**26 November 2026 · Experiment 001 · Live synthetic benchmark · `PILOT_INCONCLUSIVE`**

The baseline configuration rejected 33 of 36 live responses under strict validation. It produced zero pairs with two valid responses. This run records a delivery constraint for the ADR review workflow and leaves the paired latency, token and semantic-quality comparisons open.

## Setup

| Item | Value |
| --- | --- |
| Local run | `20261126T125346Z-w4ppe43m` |
| Model | `Qwen3.5-4B-UD-Q5_K_XL.gguf` |
| GGUF SHA-256 | `b4c36a8e14a80c21bcab5a067ce342b2e70e28f60b4aa95ad12203fa17b87426` |
| Runtime | llama.cpp `0.3.0` build `10621`, commit `c1d0e7a00` |
| Benchmark and dataset | [Pinned EDH revision `38bc939`](https://github.com/edh-project/edh-adr-preflight/tree/38bc939a1c270667805bf42504c29096771a8048) |
| Protocol | Six labeled synthetic cases, two representations, three repetitions per case and representation |
| Generation | Temperature 0, maximum 1,024 output tokens, 8,192-token context, server reasoning budget configured at 256, prompt caching disabled |

Each pair used the same model, case and decoding configuration. The JSON/JSONL switch applied to both input and output. The preceding 12-request smoke run yielded one valid response and is excluded from the 36-request table.

## Observed outcomes

| Format | Requests | Valid | Exact | TP | FP | FN | `length` + `ValueError` | `stop` + `JSONDecodeError` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| JSON | 18 | 3 | 3 | 6 | 0 | 9 | 9 | 6 |
| JSONL | 18 | 0 | 0 | 0 | 0 | 15 | 6 | 12 |
| Total | 36 | 3 | 3 | 6 | 0 | 24 | 15 | 18 |

- **15 responses reached the output limit.** The benchmark rejects incomplete responses before parsing.
- **18 responses reported `stop` and failed JSON decoding.** The failure class is observed. The exact output patterns remain unverified.
- **All three valid JSON responses matched the labels exactly.** The JSON arm returned six correct findings. The benchmark scores rejected outputs as empty, so the recorded false negatives include findings lost at the response boundary.
- **Zero of 18 pairs had two valid responses.** The paired latency and token deltas are unavailable by the benchmark's predeclared rule.

## Follow-up diagnostic

Run `20261126T131710Z-iqpl1f1b` used the same GGUF, benchmark revision and 1,024-token output limit. One clean ADR and one ADR with two labeled conflicts were tested under three conditions.

| Condition | Format | Valid | Exact | FP | FN | Length | Rejected after `stop` | Thinking observed |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | JSON | 0/2 | 0/2 | 0 | 2 | 1 | 1 | 2/2 |
| Baseline | JSONL | 0/2 | 0/2 | 0 | 2 | 1 | 1 | 2/2 |
| Thinking disabled | JSON | 2/2 | 1/2 | 1 | 0 | 0 | 0 | 0/2 |
| Thinking disabled | JSONL | 2/2 | 1/2 | 1 | 0 | 0 | 0 | 0/2 |
| Thinking disabled with `records` JSON schema | JSON | 0/2 | 0/2 | 0 | 2 | 0 | 2 | 0/2 |

The two baseline responses that finished with `stop` began with a literal `</think>` in the final content. With thinking disabled, all four plain-format responses passed validation at the same token limit. Each format still produced one false positive. Subsequent inspection identified the same extra `P1/C1` pair on the clean ADR in both formats.

The `records` schema produced JSON syntax accepted by the JSON decoder. In the conflict example, the model emitted two `complete` records and no findings. The schema allowed each array item independently. The existing validator caught the invalid sequence. This exposes a missing cross-record constraint in the schema contract.

The two jointly valid plain-output pairs yielded median JSONL minus JSON deltas of +55.3 ms and +9 tokens. The sample establishes that the two formats can be compared in this configuration. A larger paired run is needed for a format decision.

## Findings-only schema diagnostic

Run `20261126T132928Z-wwqxla2j` used the same two labeled ADRs, the pinned Qwen 4B GGUF and a 1,024-token limit with thinking disabled. The JSON schema returned a single `findings` array. The client required a complete API response and checked the allowed references and duplicate findings.

| Case | Valid | Exact | True positives | False positives | False negatives |
| --- | ---: | ---: | ---: | ---: | ---: |
| ADR with two labeled conflicts | 1/1 | 1/1 | 2 | 0 | 0 |
| Clean ADR | 1/1 | 0/1 | 0 | 1 | 0 |
| Total | 2/2 | 1/2 | 2 | 1 | 0 |

Both responses passed the structural checks. On the clean ADR, the model incorrectly paired `P1` (“Coding agent returns a patch without production credentials.”) with `C1` (“Coding agents must not receive production credentials.”). The IDs were valid. Their relationship was compatible under the supplied texts. This is a semantic false positive on an explicit negation. The baseline clean-ADR excerpts also contain the same pair, although those responses failed parsing because of the leading thinking tag. This two-case run supports further testing of the simpler response contract.

## Explicit negation probe

Inspection of the earlier trial log confirmed the extra `P1/C1` on the clean ADR in thinking-disabled plain JSON, thinking-disabled JSONL, and findings-only JSON.

Run `negation-h_gg0g7z` compared the original findings-only prompt with a clarification about action, actor and polarity. The [probe](../../scripts/qwen4b_negation_probe.py) issued 12 requests covering the same six cases under both prompts. Within each matched pair, only the text of `P1` changed. The model, schema, token budget and thinking setting were held fixed.

| Prompt | Structurally valid | Exact | False positives | False negatives | Both sides correct |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original | 6/6 | 5/6 | 1 | 0 | 2/3 |
| Clarified | 6/6 | 5/6 | 1 | 0 | 2/3 |

| Candidate phrasing | Compliant side | Violating side |
| --- | --- | --- |
| Returns a patch without credentials / after receiving credentials | `P1/C1` falsely flagged | `P1/C1` correctly flagged |
| Does not receive / receives credentials | Correctly empty | `P1/C1` correctly flagged |
| Credentials will not be issued / will be issued to the agent | Correctly empty | `P1/C1` correctly flagged |

Both prompts produced the same findings on every case. The observed false positive was specific to the tested compliant wording combining patch return and absence of credentials. The model handled the two tested direct negations correctly. The prompt clarification did not fix the error. The probe tests one synthetic rule with one request per case and prompt, so it does not establish general semantic reliability.

## Paired retest with thinking disabled

Run `20261126T135001Z-7sfpob1h` used the same pinned Qwen 4B GGUF and benchmark revision. The diagnostic ran six synthetic ADR/code cases with three repetitions and both plain formats, for 18 requests per format. Both representations changed together on the input and output sides. Thinking was disabled and the output limit was 1,024 tokens. This run used the strict parser with a final `complete` record. It did not use the findings-only schema.

| Format | Requests | Valid | Exact | FP | FN | Rejected after `stop` | Reached output limit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| JSON | 18 | 12 | 3 | 12 | 6 | 6 | 0 |
| JSONL | 18 | 18 | 9 | 12 | 0 | 0 | 0 |

Both formats completed without length-limit failures. JSONL passed strict output validation in all 18 requests. All six JSON rejections reported `stop`. The displayed `code-clean` example contained a finding but omitted the required `complete` record. The report includes one representative output; it does not establish the individual cause of every rejected reply. The scorer counts rejected replies as empty. The six JSON false negatives were recorded on rejected replies; none were recorded on a valid reply.

Of 18 matched pairs, 12 had two valid replies. In that subset the median JSONL minus JSON delta was **+27.0 ms** and **+8.5 total tokens**. These are descriptive deltas on jointly valid replies. This run provides evidence of higher parse success under the tested configuration. It does not establish a resource saving, an effect specific to input or output encoding, or general semantic accuracy.

The clean ADR reproduced `P1/C1` on all three repetitions in both arms. The clean code-boundary case added `P1/C1` and `P1/C2` in all three repetitions in both arms. `code-clean` had the extra `P1/C1` in all three JSONL repeats, and `adr-rollback-conflict` had an extra `P1/C2` in all three JSON repeats. Both arms had 12 false positives on accepted output. The three repetitions per case are not independent evidence across 18 different cases.

## Local comparison smoke test

The first comparison-procedure smoke on profile `qwen4b` (run `qwen4b.GCJeyF`) used one pass over six cases in both formats. The server started with the deprecated `--chat-template-kwargs` thinking switch. Exit status 1 reflected two rejected replies. All 12 trial rows and the summary were produced.

| Format | Valid | Exact | TP | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: |
| JSON | 4/6 | 1/6 | 3 | 4 | 2 |
| JSONL | 6/6 | 3/6 | 5 | 4 | 0 |

Among four jointly valid pairs, median JSONL minus JSON was +29.1 ms and +8.5 total tokens. The smoke run uses one repetition; its reported verdict was `PILOT_INCONCLUSIVE`. The measured comparison across models will use the runtime-supported `--reasoning off` flag on every profile.

### Qwen 27B smoke test

Run `qwen27b.elD9WS` completed one repetition of the same six labeled cases per format using the local comparison procedure. The server was launched with `--reasoning off`.

| Format | Valid | Exact | TP | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: |
| JSON | 6/6 | 5/6 | 5 | 1 | 0 |
| JSONL | 6/6 | 5/6 | 5 | 1 | 0 |

All six pairs had two valid responses. The paired median JSONL minus JSON was +109.4 ms and +7.5 total tokens. Neither format had an exclusive exact match. Per-trial inspection below confirmed the same false positive in both formats. This one-repetition smoke remains descriptive; the benchmark reported `PILOT_INCONCLUSIVE`.

### Gemma 31B smoke test

Run `gemma31b.ncqyuO` completed one repetition on the same six labeled cases in both formats. The served alias was checked before the run.

| Format | Valid | Exact | TP | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: |
| JSON | 0/6 | 0/6 | 0 | 0 | 5 |
| JSONL | 6/6 | 5/6 | 5 | 1 | 0 |

All six JSON responses failed validation. The scoring rule treats a rejected response as empty, so JSON's zero false positives and five false negatives describe the scoring fallback. The aggregate does not reveal what the rejected responses contained or why each failed. With zero jointly valid pairs, paired latency and token deltas are unavailable. The benchmark reported `PILOT_INCONCLUSIVE`.

All three local smoke runs accepted 6/6 JSONL replies. JSON validity varied by profile in these runs (Qwen 4B 4/6, Qwen 27B 6/6, Gemma 31B 0/6). The earlier Qwen 4B smoke used the deprecated thinking flag. Repeat the measured comparison with the same launch procedure across profiles.

### Cross-model review of individual trials

All three models returned the same false positive, `P1/C2`, on the clean `code-clean-boundary` case in JSONL. `P1` calls `pipeline.deploy(patch)` only when `approved is True`. `C2` prohibits the agent from calling deploy directly. The corpus has a second record, `P2`, in which the agent only generates the patch. The labeled result is empty. Qwen 27B also returned this pair in JSON, so its two smoke false positives were the same finding. Both valid Qwen 4B formats additionally flagged `P1/C1` on this case.

Gemma's six rejected JSON trials all returned `finish_reason=stop`. Four failed JSON decoding (`adr-conflict`, `adr-rollback-conflict`, `code-conflict`, `code-clean-boundary`). Two produced a `ValueError` after `stop` (`code-clean`, `adr-clean`). The saved log does not record raw responses or exception messages for this harness. The two `ValueError` results do not identify the violated contract check.

A confirmation rule based solely on agreement between Qwen 4B and either second model would have retained `P1/C2` on this case. Preserve the case as a cross-model regression and assess actor and call-path evidence independently before interpreting agreement as confirmation. The logs show agreement on the erroneous finding. They do not reveal why the models agreed.

### Gemma response-format and actor probe

Run `actor-gemma31b.ribl8n35` used the [local probe](../../scripts/qwen_gemma_actor_probe.py) with the same benchmark revision and 1,024-token output limit. Two JSON cases were rerun with raw responses recorded. Both ended with `stop`.

| JSON case | Response | Strict JSON outcome |
| --- | --- | --- |
| `code-clean` | A single `complete` object with count 0 | `ValueError: Invalid result envelope`. The contract requires an array. |
| `adr-conflict` | Three newline-delimited objects containing both expected findings and the completion record | `JSONDecodeError: Extra data` at line 2. |

For each of the six original Gemma cases, the JSON and JSONL responses have the same SHA-256 in the smoke log. The two raw JSON samples above match those hashes. The clean sample also matches `adr-clean`. The conflict sample matches `code-conflict`. The JSONL actor probe's clean response matches the hash for `code-clean-boundary` in both arms. For the six smoke cases, the strict output contract explains the observed JSON/JSONL score gap on identical response bytes. In the JSONL arm, five outputs matched their labels and the boundary case remained a false positive.

In the two-case JSONL actor probe, Gemma returned identical valid outputs with `P1/C2`. The label is empty when `pipeline.deploy(patch)` is called after approval and contains `P1/C2` when `agent.deploy(patch)` replaces it. The direct agent call was flagged correctly and the compliant pipeline call was falsely flagged. Both candidates were tested once. Qwen 27B and Qwen 4B actor-probe results are pending.

## Remaining checks

Keep JSONL with thinking disabled as a candidate profile for producing review suggestions. Preserve the repeatable clean-case false positives as regressions. Before extending its role, evaluate the profile on a larger set of independently labeled cases and assess how often a second reviewer confirms or rejects its findings. Measure end-to-end latency and tokens including any second review. Evaluate the findings-only schema separately.

Sources are the developer's local pilot, diagnostic, negation, paired retest, local comparison smoke logs, and the Gemma actor-probe report. The original per-request files remain with the local runs. See [Experiment 001](https://github.com/edh-project/edh-adr-preflight/pull/2) for the protocol.
