# Live ADR matched-pair evidence

**2026-11-26 · Local synthetic evaluation.** Both inputs were classified as `Risk: low` to isolate the effect of model findings from the policy's high-risk rule. Both used the same accepted baseline and passed the structural lint shared by the pull request check.

Base revision [`dcbd92b`](https://github.com/edh-project/edh-adr-preflight/tree/dcbd92b098fefc3f5e569ad992cba60cc7ee8c5c), llama-server 0.3.0 (build 10621, commit `c1d0e7a00`), loopback inference on an Apple Silicon Mac. The runs used temperature 0, one slot, an 8,192-token context and a server reasoning budget of 256 tokens.

## Run 1 — published adapter

Qwen3.8-27B-UD-Q5_K_XL was the primary reviewer and gemma-4-31B-it-qat-UD-Q4_K_XL was the independent reviewer. Both model calls completed for both cases. The policy rejected their JSON responses during validation and routed both cases to human review.

| ADR | Structural findings | Qwen and Gemma validation | Preflight decision | Execution authorized |
| --- | ---: | --- | --- | --- |
| Compatible | 0 | Both `ValueError` | `REVIEW` (reviewer failure) | `false` |
| Conflict | 0 | Both `ValueError` | `REVIEW` (reviewer failure) | `false` |

A diagnostic repeat of the two Gemma calls identified `Invalid finding fields`. Its objects used `type`, `description` and `evidence` instead of the declared fields. The conflict response identified direct issuance of production credentials to a coding agent.

## Run 2 — schema envelope only

The experiment changed only the request envelope to `response_format.json_schema`, following the [llama.cpp structured-output test](https://github.com/ggml-org/llama.cpp/blob/master/scripts/server-test-structured.py). The schema, exact-quote validation, prompt and inputs were held fixed. This run called Gemma directly to isolate the transport and validator.

| ADR | Gemma validation | Accepted findings |
| --- | --- | --- |
| Compatible | Passed · 35.153 s | `ambiguity` about an explicit baseline reference and `risk` about missing negative tests |
| Conflict | Passed · 25.508 s | One `critical` `conflict` against ADR-0001 |

Gemma's accepted quote from the conflicting ADR:

> The coding agent may obtain short-lived production deployment credentials directly after human approval.

The baseline allows the deployment pipeline alone to receive those credentials after human approval. The experiment demonstrates a grounded conflict beyond lint. The compatible ADR also drew validly shaped findings and would still route to `REVIEW` under the current policy.

## Run 3 — complete local preflight with the corrected adapter

The follow-up used Gemma as primary and Qwen as independent reviewer. It clarified the common context and acceptance criteria in both inputs, keeping the low-risk label and changing only the final decision sentence between cases. The transport request was equivalent to the code proposed in this PR.

| ADR | Structural findings | Gemma validation | Qwen validation | Preflight decision | Execution authorized |
| --- | ---: | --- | --- | --- | --- |
| Compatible | 0 | ok · 1 findings (0 conflict) | ok · 10 findings (0 conflict) | `REVIEW` | `false` |
| Conflict | 0 | ok · 1 findings (1 conflict) | ok · 20 findings (2 conflict) | `REVIEW` | `false` |

Both reviewers returned validated `conflict` findings for the conflicting ADR and zero `conflict` findings for the compatible ADR. Both cited the same exact sentence quoted above. On the compatible ADR, ambiguity, missing contracts and risk findings still triggered `REVIEW` under the current policy. The finding categories distinguished this pair. The aggregate preflight decisions were identical.

For this repeat, replace the context with `ADR-0001 defines the production credential boundary. This ADR documents how ephemeral coding workspaces and the deployment pipeline apply that boundary.` Replace the shared acceptance criteria with:

> Integration tests attempt to acquire production credentials using the coding-agent identity and the deployment-pipeline identity, before and after human approval. Verify that each case is allowed or denied exactly as specified in the Decision section. In particular, verify denial for identities and approval states outside the permitted case.

## Inputs

For runs 1 and 2, use [ADR-0001](https://github.com/edh-project/edh-adr-preflight/blob/dcbd92b098fefc3f5e569ad992cba60cc7ee8c5c/adr/accepted/ADR-0001.md) as the accepted baseline and [ADR-0002](https://github.com/edh-project/edh-adr-preflight/blob/dcbd92b098fefc3f5e569ad992cba60cc7ee8c5c/adr/proposed/ADR-0002.md) as the proposed document. Keep `Risk: low` in both variants and replace the acceptance criteria paragraph with this line:

> An integration test verifies that production credentials can be issued only to the identity and under the conditions specified in this decision.

Set the first two sentences of the decision in both variants to `Use ephemeral workspaces with read-only repository access. The coding agent returns a patch for review.` The final decision sentence is the only difference:

| Variant | Final decision sentence |
| --- | --- |
| Compatible | Only the deployment pipeline may obtain short-lived production deployment credentials after human approval. |
| Conflict | The coding agent may obtain short-lived production deployment credentials directly after human approval. |

Run the existing low-risk `clean` live case once per variant in an isolated checkout, with the same accepted baseline and adaptive routing. Apply one candidate at a time. For the transport-only repeat, call `live_review` and `validate_review` on each variant with Gemma alone.

These synthetic pairs verify the transport fix and show a grounded conflict beyond lint. Reliable automatic routing for compatible changes still needs evaluation.
