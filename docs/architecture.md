# Architecture and trust boundaries

## End-to-end target architecture

```mermaid
flowchart TD
  PR[GitHub pull request: proposed ADR] --> CI[GitHub Actions: ADR preflight]
  CI --> L[Deterministic structural checks]
  L -->|Valid| MR[Model router: trusted local execution]
  L -->|Invalid| X[REJECT]
  subgraph Local[Self-hosted inference on isolated trusted host]
    MR --> Q[Qwen 27B: primary]
    MR --> T[Optional Qwen 4B: triage]
    MR --> G[Gemma 31B: conditional independent review]
  end
  Q --> R[Structured validation report]
  G --> R
  T --> R
  R --> P[Deterministic admission policy]
  P --> A[ALLOW: preflight pass]
  P --> H[REVIEW: human resolution]
  P --> X
  A --> C[Draft execution contract]
  C -.-> AP[Human approval and signed runtime authorization: future]
  AP -.-> AG[Coding agents: future]
  AG -.-> D[CI/CD to AWS or GCP: future]
```

The fixture CI does not call a model. The live CLI and hosted BYOI manual action are designed to run the same three synthetic examples through operator-configured inference; the private-only workflow is an inactive template. Real model runs remain unverified. The separate PR structural workflow reads changed proposed ADRs as data using the base revision policy and baseline; structurally valid proposals stay REVIEW until semantic review. It does not call a model. The solid lines represent PoC logical components, not a deployed end-to-end integration; dashed lines are explicitly out of scope. `ALLOW` is not permission to execute.

## Detailed routing and policy

```mermaid
flowchart TD
  S[Proposed ADR plus accepted baseline] --> L[Stage 1: deterministic lint]
  L -->|Invalid| X[REJECT: no model calls]
  L -->|Valid| T{Triage configured?}
  T -->|Yes| Q4[Optional Qwen 4B review]
  T -->|No| Q[Mandatory primary review: Qwen 27B]
  Q4 --> Q
  Q --> E{High risk, finding, failure or always independent?}
  E -->|Yes| G[Conditional independent review: Gemma 31B]
  E -->|No| P[Stage 3: deterministic policy]
  G --> P
  P --> V[Validate report shape and exact evidence quotes]
  V -->|Failure, finding or high risk| R[REVIEW]
  V -->|Valid low risk and no findings| A[ALLOW]
  A --> C[Draft contract example for ADR-0002 only]
  R --> H[Human review required]
  C --> H
```

Review shape and quotations are actually checked before the escalation decision as well as being inputs to policy. Exact quote matching does not prove the model interpretation correct. A high-risk classification is not inferred automatically; the demo reads the ADR risk field. No workflow grants credentials or executes a patch.

## Trust and exposure

- Only synthetic ADRs and reports belong in this demonstration repository; do not commit private material.
- No organization-wide token, private reusable workflow, internal EDH data or production secret.
- Active CI runs on GitHub-hosted Ubuntu. The private-only local-runner workflow is stored outside the active workflows directory as an example. Never attach a self-hosted runner to this public demo, including through organization runner groups.
- The local CLI defaults to loopback HTTP; the hosted BYOI manual action requires HTTPS endpoints configured by repository operators through Variables, with credentials in Secrets. Ports and model IDs are configurable. Proxies and redirects are disabled. Model outputs are untrusted, not policy authorities.
- The policy records source and code hashes for auditability; these are not signed attestations. PR workflows are not an immutable enforcement boundary unless protected by independent repository or organization policy.
- Production integration requires immutable workflow enforcement, bounded semantic review of changed ADRs, isolated execution, signed authorization, an acceptance dataset and independent verification.

## Evidence

Each GitHub Actions summary distinguishes fixture from live results and includes candidate, decision, expected fixture outcome, reviewer role, requested/reported model, timings, token usage when available, findings and source quotes. JSON artifacts contain hashes and the draft contract example. No claims about real model accuracy follow from fixture tests.
