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

## Remaining checks

Run the separate 36-request plain JSON versus JSONL comparison with thinking disabled. A further semantic check can keep the patch-return action fixed and vary how the credential boundary is expressed. Preserve the unresolved wording as a regression and report semantic errors alongside output validation.

Sources are the developer's local `pilot/report.md`, counts and references from trial logs, and the follow-up diagnostic and negation reports. The per-request files remain with the local runs. See [Experiment 001](https://github.com/edh-project/edh-adr-preflight/pull/2) for the protocol.
