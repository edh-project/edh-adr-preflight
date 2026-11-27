# R10 — Cost-Efficient Architectural Governance in Agentic SDLC

**Evaluating Small Language Models, Structured Architectural Context, and Multi-Tier Inference Cascades**

EDH Project · A-SDLC Research Portfolio · Candidate research proposal · 26 November 2026

[Research portfolio R01–R09 (Wiki)](https://github.com/edh-project/edh-adr-preflight/wiki/A-SDLC-Research-Portfolio)

**Status:** candidate; value unassessed; priority TBD; owner unassigned. Related to R01, R03, R04, R05 and R06. This is not an Experiment 004 authorization or a validated production capability.

## Engineering overview — why this research matters

In an agentic SDLC, a proposed architectural decision can trigger costly planning, implementation, testing and review. Finding contradictions after implementation begins wastes both engineering time and model inference. Sending every proposal and its context to a premium cloud model is not necessarily the best alternative.

For a Senior or Staff Engineer, R10 is an investigation of an upstream, model-agnostic control point in an internal developer platform (IDP): apply deterministic rules first; use a small local model for bounded semantic checks against known policies and accepted ADRs; escalate unresolved or high-risk cases to stronger models or human reviewers. The aim is not to make a 4B model behave like a frontier model, but to establish which workloads require which level of reasoning, and what it costs to deliver them reliably.

### R10-A — Structured Context Engineering for Small Language Models

Can the representation and selection of the same architectural knowledge improve the useful capability of a small quantized model? Compare Markdown, JSON and JSONL with matched facts, fixed model settings and independently labelled outcomes; isolate retrieval, token budget, model size and quantization in subsequent comparisons.

![R10-A — context-format comparison](assets/16-overview-context-engineering.svg)

*Figure O1. Proposed controlled comparison. No format is assumed superior.*

[Mermaid source](assets/16-overview-context-engineering.mmd)

### R10-B — Enterprise Inference Cost Optimization through Multi-Tier Model Cascades

Can reliable bounded checks be handled locally to avoid expensive cloud calls without weakening governance? The illustrative Section 8 scenario has 10,000 small-local requests, of which 2,000 reach a larger local tier and 1,000 reach premium cloud. The modeled costs are USD 1,040 cloud-only and USD 294 hybrid, including assumed fixed and variable inference costs.

![R10-B — illustrative routing and cost comparison](assets/17-overview-inference-economics.svg)

*Figure O2. Synthetic example, not measured EDH performance. Quality parity remains unproven.*

[Mermaid source](assets/17-overview-inference-economics.mmd)

The 71.7% modeled reduction applies to this eligible workload, not to the entire company. If the workload accounts for 20% of baseline LLM expenditure, the overall net reduction relative to that baseline is approximately 14.3%.

![Overall budget savings equation](assets/19-overview-budget-equation.svg)

A 10–15% overall reduction is an exploratory business hypothesis: at the illustrative workload saving, roughly 14–21% of baseline spend must be eligible. Actual cloud invoice savings and net TCO savings must be reported separately. Account for additional operations, review, failures and caching; compare against economical cloud alternatives, not just premium models. Unaffected workloads are assumed unchanged.

### How the workstreams connect

![Connection between context engineering and inference economics](assets/18-overview-research-connection.svg)

*Figure O3. Proposed causal chain; every link must be tested.*

[Mermaid source](assets/18-overview-research-connection.mmd)

| Workstream | Engineering outcome | Business question |
| --- | --- | --- |
| R10-A | Capability boundaries by format, task, model and quantization | Which checks can safely move to inexpensive inference? |
| R10-B | Calibrated routing, resource profile and quality-matched TCO | Does delegation materially reduce platform operating costs? |

Preflight remains advisory. Critical risk, missing evidence, external disclosure restrictions and required human approval override cost optimization.

## Abstract

Agentic software engineering introduces an architectural governance challenge: keeping proposed decisions consistent with organizational architecture, security policies, infrastructure constraints and accepted ADRs before implementation begins. Systematic use of frontier models for every validation request may add cost, latency, external dependency and disclosure risk. This proposal investigates whether locally deployed quantized small language models (SLMs), operating inside deterministic verification and risk-aware routing, can reliably perform a meaningful proportion of architectural preflight before escalation. Qwen3.5-4B Q5 is the initial candidate, not the research boundary. The objective is to identify minimum sufficient intelligence, capability limits, quality–cost trade-offs and safe escalation criteria, not replace architects or claim empirical results.

## 1. Research objective

Determine the minimum sufficient inference capability for reliable architectural preflight, minimizing total sustainable operational cost without compromising governance.

![Four research dimensions](assets/09-research-dimensions.svg)

*Four research dimensions.*


## 2. Existing research and market evidence

| Research | Relevance |
| --- | --- |
| [Small Language Models are the Future of Agentic AI](https://arxiv.org/abs/2506.02153), NVIDIA Research, 2025 | Specialized small models for repetitive agentic workloads |
| [FrugalGPT](https://arxiv.org/abs/2305.05176), 2023 | Cost-aware inference cascades |
| [RouteLLM](https://arxiv.org/abs/2406.18665), 2024/2025 | Dynamic routing between weaker and stronger models |
| [Small Language Models for Agentic Systems](https://arxiv.org/abs/2510.03847), 2025 | SLM-first architectures and operational efficiency |
| [Evaluating Large Language Models for Detecting Architectural Decision Violations](https://arxiv.org/abs/2602.07609), 2026 | Reported post-implementation compliance study, 980 ADRs and 109 repositories |

The proposed contribution is specifically pre-implementation governance using structured architectural evidence, deterministic verification and local quantized inference. Existing compliance studies do not establish preflight accuracy. Literature claims and pricing snapshots are inherited from the proposal draft and should be reverified in the formal literature review.

### 2.1 Published capability indicators

| Benchmark | Qwen3.5-4B | Qwen3.5-9B |
| --- | ---: | ---: |
| IFEval | 89.8 | 91.5 |
| MMLU-Pro | 79.1 | 82.5 |
| GPQA Diamond | 76.2 | 81.7 |
| IFBench | 59.2 | 64.5 |
| LongBench v2 | 50 | 55.2 |
| BFCL v4 | 50.3 | 66.1 |
| DeepPlanning | 17.6 | 18 |

![Publisher-reported Qwen benchmarks; not quantized or ADR-specific results](assets/04-capability-profile.svg)

*Publisher-reported Qwen benchmarks; not quantized or ADR-specific results.*


Source: [Qwen model card](https://huggingface.co/Qwen/Qwen3.5-4B). Strong instruction-following results motivate bounded workload experiments; complex planning and tool use remain distinct capabilities. General benchmark scores do not predict ADR accuracy.

### 2.2 Quantization and hardware efficiency

| Quantization | File GB | Generation tok/s | Relative perplexity increase |
| --- | ---: | ---: | ---: |
| FP16 | 8.42 | 36.8 | baseline |
| Q8_0 | 4.48 | 54 | 0.18% |
| Q6_K | 3.46 | 62 | 0.54% |
| Q5_K_M | 3.11 | 56.6 | 1.74% |
| Q4_K_M | 2.71 | 58.5 | 4.07% |

![Community M2 Ultra quantization measurements; not EDH measurements](assets/05-quantization-profile.svg)

*Community M2 Ultra quantization measurements; not EDH measurements.*


Source: [AtomGradient community benchmark](https://atomgradient.github.io/apple-silicon-llm-inference/). Q5 reduced file footprint by about 63% relative to FP16; Q6 was faster and less degraded in this particular report. Perplexity is not task accuracy. File size excludes runtime memory. Pin artifact hash, quantizer and runtime; confirm actual latency, memory and task quality.

### 2.3 Model comparison matrix

| Candidate | Experimental role |
| --- | --- |
| Qwen3.5-2B | Lower capacity boundary |
| [Qwen3.5-4B Q5](https://huggingface.co/unsloth/Qwen3.5-4B-GGUF) | Primary candidate |
| [Gemma 3 4B IT](https://gemma.ai/models/gemma-3/) | Alternative model family |
| Qwen3.5-9B | Intermediate tier |
| Local 27–31B | Higher-capability reasoning |
| Commercial cloud models | Budget and premium baselines |

## 3. Position within the Agentic SDLC

![Figure 1. Upstream architectural control point](assets/01-sdlc-control-point.svg)

*Figure 1. Upstream architectural control point.*

```mermaid
flowchart TD
 A[Business / engineering intent] --> B[Proposed ADR] --> C[EDH architectural preflight] --> D[Architectural approval] --> E[Agentic implementation] --> F[Delivery and runtime compliance]
```

Preflight is advisory, distinct from architectural approval and downstream runtime compliance.

## 4. Research questions and hypotheses

| ID | Research question |
| --- | --- |
| RQ-01 | Minimum sufficient model capacity by workload? |
| RQ-02 | Does structured context improve quality over semantically identical unstructured context? |
| RQ-03 | How do quantization levels affect quality, latency, memory and energy? |
| RQ-04 | What share can be locally resolved at bounded error? |
| RQ-05 | When does local or hybrid inference outperform cloud-only economically? |
| RQ-06 | Does early feedback reduce downstream implementation rework? |

H1: bounded workloads can be delegated to SLMs. H2: structured context and retrieval improve performance without increasing parameters. H3: evidence verification and calibrated routing reduce reliance on larger models while bounding risk. H4: local or hybrid inference can reduce cost per correct validation at sufficient utilization. H5: early contradiction detection may reduce rework. All are falsifiable, not results.

## 5. Multi-tier inference architecture

![Figure 2. Inference cascade; mandatory human review overrides all early exits](assets/02-inference-cascade.svg)

*Figure 2. Inference cascade; mandatory human review overrides all early exits.*

```mermaid
flowchart TD
 A[Proposed ADR + versioned context] --> B[Deterministic checks]
 B -->|Deterministic result| J[Preflight result - not approval]
 B -->|Semantic check| C[Small local model]
 C --> D{Evidence and risk gate}
 D -->|Verified low risk| J
 D -->|Uncertain or complex| E[Larger local model]
 D -->|Mandatory review| I[Human review]
 E --> F{Second evidence and risk gate}
 F -->|Verified low risk| J
 F -->|Unresolved| G{External disclosure permitted?}
 G -->|Yes| H[Approved cloud model]
 G -->|No| I
 H --> I --> J
```

Deterministic checks take precedence. Versioned context contains accepted ADRs, policies and evidence. Verify references and quotations, validate schemas, and independently evaluate semantic support: a valid citation does not prove entailment. Escalate on evidence completeness, calibrated error rates and severity, not self-reported model confidence alone. Cloud disclosure requires explicit permission; otherwise use local or human review. No model output constitutes approval or execution authority. Treat ADR text as untrusted data and test prompt injection, stale evidence and conflicting requirements.

## 6. High-value enterprise workloads

| Workload | Expected SLM suitability | Potential value |
| --- | --- | --- |
| ADR classification and tagging | High | Metadata automation |
| Requirement and constraint extraction | High | Reusable knowledge |
| Explicit contradiction detection | High | Early feedback |
| Evidence and ADR matching | High | Traceability |
| Duplicate or overlapping ADR detection | High | Reduced fragmentation |
| Missing architectural considerations | Conditional | Completeness |
| Component dependency analysis | Conditional | Integration risks |
| Implicit security implications | Limited | Preliminary screening |
| Distributed system failure analysis | Limited | Escalation candidate |
| Autonomous architecture approval | Out of scope | Organizational accountability |

These are hypotheses. Prefer reliable deterministic rules where possible.

## 7. Experimental methodology

![Figure 3. Context ablation experiment](assets/03-experimental-design.svg)

*Figure 3. Context ablation experiment.*

```mermaid
flowchart TD
 A[Frozen labelled ADR corpus] --> B[A: ADR only]
 A --> C[B: Markdown context]
 A --> D[C: identical JSONL facts]
 A --> E[D: JSONL + retrieval]
 B --> F[Identical inference settings]
 C --> F
 D --> F
 E --> F
 F --> G[Blind evaluation against gold labels]
 G --> H[Quality, cost, latency and risk]
 H --> I[Deployment decision]
```

| Comparison | Isolated variable |
| --- | --- |
| A vs B | Availability of architectural context |
| B vs C | Representation of identical facts |
| C vs D | Retrieval and context selection |
| B vs E | Markdown vs JSON with identical facts |
| C vs E | JSONL vs JSON with identical facts |

Arm E (ADR + identical facts in JSON) is a proposed extension of the original A–D design. Figure O1 depicts the additional format-only comparison; keep retrieval and semantic facts fixed across B, C and E.

Freeze prompts, context versions, model hashes, runtime, seeds and settings. Match semantic facts in Markdown/JSONL; report token counts and token-budget-matched sensitivity. Separate thinking/non-thinking. Compare Q4/Q5/Q6/Q8 and optional BF16 on identical cases. Include deterministic-only, direct larger local, direct budget cloud, direct premium cloud and cascade baselines. Independently label cases with expert adjudication, not model-as-ground-truth. Separate calibration from final holdout; repeat seeds and use paired confidence intervals. Include critical and adversarial cases.

![Proposed pilot dataset: 20 cases in each of six categories](assets/06-pilot-corpus.svg)

*Proposed pilot dataset: 20 cases in each of six categories.*


120 cases is a feasibility pilot, not certification of production safety. Expand independent holdout before any automatic blocking or acceptance.

## 8. Enterprise inference economics

[GitHub-hosted inference economics and feasibility](github-inference-economics.md) — measured local pilot summary, dated GitHub runner rates, batch-cost sensitivity and proposed hosted benchmark.

Compare cost per correctly resolved validation at equivalent quality, risk and service levels, not only cost per token. Example workload: 10,000 requests/month, 8,000 uncached input and 1,000 billed output tokens per cloud call.

| Draft cloud pricing snapshot | Input USD / 1M | Output USD / 1M | Example monthly USD |
| --- | ---: | ---: | ---: |
| GPT-6.2 Astra | 8 | 40 | 1,040 |
| GPT-6.2 Sol | 2 | 10 | 260 |
| Claude Opus 5.5 | 4 | 20 | 520 |
| Claude Sonnet 5.5 | 2 | 10 | 260 |
| Claude Haiku 5.5 | 0.10 | 0.50 | 13 |

Source links: [OpenAI pricing](https://developers.openai.com/api/docs/pricing), [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing). These draft rate inputs have **not been independently reverified for this publication**; reprice before decisions. Include caching, batch discounts, billed reasoning and retries.

Hybrid example: fixed local $150/month, $0.002 per SLM request, 20% reach larger local at $0.01, 10% reach premium cloud at $0.104. Cloud is a subset of larger-local escalation. Total $294 versus $1,040 for premium-only (71.7% illustrative reduction). Hybrid is more expensive than budget cloud in this example; quality parity is not demonstrated. Human review, differential operations and error costs are excluded.

![Illustrative premium cloud versus hybrid costs](assets/07-monthly-cost.svg)

*Illustrative premium cloud versus hybrid costs.*


For monthly volume N, fixed cost F, per-request small-local cost v_s, larger-local cost v_l and cloud cost c, with unconditional escalation fractions r_l and r_c:

**Hybrid monthly cost**

![Hybrid monthly cost: Hybrid monthly cost equals fixed monthly cost plus monthly request volume times the sum of small-local unit cost, larger-local escalation cost and cloud escalation cost.](assets/12-hybrid-monthly-cost.svg)

**Cloud-only monthly cost**

![Cloud-only monthly cost: Cloud-only monthly cost equals request volume times cloud unit cost.](assets/13-cloud-monthly-cost.svg)

**Break-even condition (hybrid strictly cheaper than cloud-only)**

![Monthly break-even volume: Monthly request volume must exceed fixed monthly cost divided by the positive savings per request.](assets/14-break-even-volume.svg)

The escalation fractions satisfy $0 \le r_c \le r_l \le 1$: cloud requests are a subset of larger-local requests. All costs use the same currency and accounting period.

The denominator must be positive; illustrative Astra break-even is about 1,675 validations/month. Evaluate 1k/10k/100k workloads, utilization, concurrency and service-level constraints. The same formula supports sensitivity analysis across cloud rates, prompt sizes and escalation fractions.

![Total cost of ownership components](assets/10-enterprise-tco.svg)

*Total cost of ownership components.*


TCO includes amortization, redundant capacity, electricity/cooling, monitoring, upgrades, on-call, retries, audit, review and failure/rework. **Cost per correctly resolved validation**

![Cost per correctly resolved validation: Total attributable cost divided by the number of correctly resolved validations.](assets/15-cost-per-correct-validation.svg)

The metric is undefined when there are no correctly resolved validations. Include human review where required.


<details>
<summary>Native mathematical notation and editable LaTeX source</summary>

**Hybrid monthly cost**

$$
C_{\mathrm{hybrid}}=F+N\left(v_s+r_l v_l+r_c c\right)
$$

**Cloud-only monthly cost**

$$
C_{\mathrm{cloud}}=Nc
$$

**Monthly break-even volume**

$$
N>\frac{F}{(1-r_c)c-v_s-r_l v_l}
$$

**Cost per correctly resolved validation**

$$
C_{\mathrm{correct}}=\frac{\text{Total attributable cost}}{\text{Correctly resolved validations}}
$$

[LaTeX source file](assets/economics-equations.tex)

</details>

## 9. Metrics and pilot criteria

| Metric | Proposed target |
| --- | --- |
| Explicit violation recall | ≥95% |
| Violation precision | ≥90% |
| Implicit violation recall | ≥75% |
| Correct abstention with insufficient evidence | ≥85% |
| Schema validity and reference integrity after checks | 100% for accepted outputs |
| Macro-F1 improvement from structured context | Explore ≥10 percentage points |
| Premium model invocation reduction | Explore ≥70% subject to risk |
| P95 latency for bounded checks | Explore ≤15 seconds |
| Cost per correct validation | Below quality-matched baseline |

Report per-class recall/precision, critical false acceptance, semantic evidence support, risk–coverage, calibration, retries, fallback, P50/P95 latency, input/output/reasoning tokens, prefill and generation throughput, peak RAM/VRAM, concurrency, energy, availability and rework. UNKNOWN is abstention, not success. Report confidence intervals and class counts.

![Conceptual risk–coverage curve — synthetic, not experimental results](assets/08-risk-coverage.svg)

*Conceptual risk–coverage curve — synthetic, not experimental results.*


The desired outcome can be higher locally resolved coverage at the same residual risk. All thresholds are exploratory; revise from evidence.

## 10. Research deliverables

![Six proposed research deliverables](assets/11-research-deliverables.svg)

*Six proposed research deliverables.*


1. Reproducible dataset and evaluation harness, capability matrix and provenance.
2. Context ablation and quantization report with uncertainty.
3. Inference resource profile and calibrated escalation boundaries.
4. Enterprise economics: sensitivity, TCO and quality-matched comparisons.
5. Advisory IDP/CI/CD integration; separate organizational approval for production admission.

## 11. Research significance

The question is not how to add an LLM to CI/CD, but how much intelligence each stage requires and how to provision it at the lowest sustainable cost without compromising architectural governance. Negative outcomes and measured limits are useful. No enterprise savings, deployment readiness or novelty priority is claimed. Research scope, ownership, budget and permitted data remain subject to Experiment 003 governance.

## 12. Interdisciplinary Research Positioning

![Potential interdisciplinary research area: context engineering, small language models, inference economics and enterprise FinOps](assets/20-interdisciplinary-research-positioning.svg)

*Figure 4. Potential interdisciplinary research area. The intersection represents a proposed applied research question, not established novelty.*

R10 combines software architecture and governance, context engineering, empirical evaluation of quantized models, and inference systems economics. Each ingredient has substantial prior art. The intended contribution is a reproducible, risk-aware investigation of their interaction in **pre-implementation architectural validation**, rather than a claim to have invented structured context or model cascades. Position the work as an industrial applied research proposal within EDH; scientific novelty, generalizability and publication suitability remain open questions.

## 13. Threats to Validity and Research Limitations

| Threat | Mitigation |
| --- | --- |
| Input format confounded with semantic content, retrieval or token count | Freeze facts, compare Markdown/JSON/JSONL directly, add token-budget-matched sensitivity tests. |
| Structured output reduces reasoning or merely improves parseability | Hold output contract fixed for input experiments; independently ablate reasoning/formatting, decoding and validation. Measure syntax and semantic correctness separately. |
| Small or synthetic corpus; class imbalance; label leakage | Separate calibration and held-out sets, use independent expert labels, report class counts and confidence intervals; expand with authorized real ADRs. |
| Routing overfit or correlated model failures | Calibrate on separate data; measure severity-specific false acceptance and abstention; keep mandatory review independent of model confidence. |
| Runtime, quantizer and hardware confounding | Pin artifacts, settings and versions; measure cold/warm, prefill/decode, peak memory, energy and concurrency. |
| Cloud comparison and cost assumptions | Compare budget, cached/batched, routed and premium baselines; use actual billed tokens and full incremental TCO; vary eligible spend and utilization. |
| External validity and knowledge governance | Do not generalize SQL/tool-call benchmarks to ADRs; repeat across model families, ADR domains and approved environments; retain disclosure boundaries. |
| Novelty and publication bias | Conduct a systematic search and extract negative results; distinguish research publications, preprints, technical guidance and vendor claims. |

The initial 120-case pilot estimates feasibility, not production safety or statistical equivalence. The 10–15% overall budget hypothesis and all target thresholds remain unvalidated. A null or negative result is a useful outcome.

## 14. References and Related Work

The [annotated bibliography and evidence register](REFERENCES.md) contains 28 selected sources with dates, provenance, workstream relevance and applicability limits. The following reading map connects the most relevant sources to specific R10 decisions:

| Source | Relevance and implication |
| --- | --- |
| [Structured Context Engineering for File-Native Agentic Systems](https://arxiv.org/abs/2602.05447), February 2026 | 9,649 experiments, 11 models, four formats; aggregate format difference was not statistically significant (p=0.484). Do not assume JSONL wins; test model-specific effects and retrieval separately. |
| [The Format Tax](https://arxiv.org/abs/2604.03616), April 2026 | Structured **output** can impair reasoning in open-weight models. Distinguish this from input-context engineering. |
| [Evaluating Large Language Models for Detecting Architectural Decision Violations](https://arxiv.org/abs/2602.07609), February 2026 | Closest architectural compliance reference; post-implementation detection is not prospective preflight. |
| [Mapping the Efficiency Landscape of Small Language Models](https://ijcai.org/proceedings/2026/627), IJCAI 2026 | 75 SLMs, five tasks; measure task-specific performance and energy. |
| [Cold Start Latency of Quantized Small Language Models on Serverless CPU Infrastructure](https://research.google/pubs/cold-start-latency-of-quantized-small-language-models-on-serverless-cpu-infrastructure/), Google Research | GGUF, CPU serving and memory tiers for models up to 3.8B; informs local service economics. |
| [Switchcraft](https://www.microsoft.com/en-us/research/publication/switchcraft-ai-model-router-for-agentic-tool-calling/), Microsoft Research, 2026 | Existing task-aware routing research; evaluate alternative routers. |
| [Scaling laws meet model architecture](https://www.amazon.science/blog/making-llms-faster-without-sacrificing-accuracy), AWS AI Labs / ICLR 2026 | Architecture matters for inference throughput even at similar parameter counts. |
| [Code for rules, models for judgment](https://aws.amazon.com/blogs/machine-learning/cut-generative-ai-costs-code-for-rules-models-for-judgment/), AWS, 17 November 2026 | Recent industrial guidance on deterministic logic and right-sized inference. |
| [Optimizing cost per task and proving agent ROI](https://aws.amazon.com/blogs/machine-learning/optimizing-cost-per-task-and-proving-agent-roi-on-amazon-bedrock/), AWS, 12 November 2026 | Cost per task and operational attribution, relevant to R10-B. |
| [From Requests to Sessions](https://systems.seas.harvard.edu/blog/agentic-traces-freeinference/), Harvard Systems Group, 4 November 2026 | Session-aware agentic workload characterization; motivates measuring growing context and caching. |

**Evidence status:** selected related work reviewed 27 November 2026; not an exhaustive search. Peer-reviewed proceedings, preprints, official research summaries, vendor guidance and dynamic price cards are explicitly distinguished in the register. Some recent sources were verified through indexed official descriptions rather than full-text access. No external benchmark demonstrates our exact Qwen3.5-4B Q5 + ADR + JSONL workflow or the proposed enterprise budget reduction.

## Source assets

All fifteen SVG illustrations and five vector equation renderings are in [assets](assets/). The three overview diagrams have editable Mermaid sources, and the [overall budget equation](assets/overview-budget-equation.tex) has LaTeX source. The economic equations also have [editable LaTeX source](assets/economics-equations.tex). Three architecture diagrams also have editable Mermaid sources: [SDLC](assets/01-sdlc-control-point.mmd), [cascade](assets/02-inference-cascade.mmd), [experiment](assets/03-experimental-design.mmd). Graphics are recreated vector illustrations, not screenshots of the chat. The GitHub edition is static; the separate HTML edition has the interactive calculator.
