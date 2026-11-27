# R10 — Annotated bibliography and evidence register

**Scope:** selected literature and industrial guidance relevant to R10-A (context/SLM capability) and R10-B (inference economics). **Reviewed:** 27 November 2026. This is a targeted related-work register, not a systematic review or proof of scientific novelty. Research abstracts, official publication records, vendor documentation and community reports have different evidential weights. Some recently indexed official articles could not be retrieved in full during this review; their entries are intentionally limited to the documented topic. Verify full text, venue, version, methodology, artifact availability and reproduction conditions before adopting numerical results.

Reference identifiers below are local bibliography keys, not EDH portfolio IDs.

### [R01] Small Language Models are the Future of Agentic AI

**Source:** NVIDIA-affiliated research; arXiv, June 2025; revised September 2026 · **Workstream:** R10-A / R10-B

[Publication / primary source](https://arxiv.org/abs/2506.02153)

Motivates specialized smaller models and heterogeneous agentic systems. A position/analysis paper, not evidence of ADR-specific accuracy.

### [R02] Small Language Models for Agentic Systems: A Survey of Architectures, Capabilities, and Deployment Trade-offs

**Source:** arXiv, October 2025 · **Workstream:** R10-A / R10-B

[Publication / primary source](https://arxiv.org/abs/2510.03847)

Survey context for SLM workloads and deployment choices; use to identify competing architectures rather than assume an implementation gap.

### [R03] Evaluating Large Language Models for Detecting Architectural Decision Violations

**Source:** arXiv, February 2026 · **Workstream:** R10-A

[Publication / primary source](https://arxiv.org/abs/2602.07609)

Closest domain-specific related work; studies violations in existing implementations, not prospective ADR admission. Reuse its taxonomy where applicable.

### [R04] Structured Context Engineering for File-Native Agentic Systems

**Source:** arXiv, February 2026 · **Workstream:** R10-A

[Publication / primary source](https://arxiv.org/abs/2602.05447)

9,649 SQL-generation experiments across 11 models and four formats; no significant aggregate format effect (p=0.484), but model-specific sensitivities. File retrieval was not uniformly beneficial. Direct motivation for matched-fact format ablations; not ADR evidence.

### [R05] The Format Tax

**Source:** arXiv, April 2026 · **Workstream:** R10-A

[Publication / primary source](https://arxiv.org/abs/2604.03616)

Shows that requiring structured output can impair open-weight model reasoning; separating reasoning and formatting can mitigate degradation. Output schema effects must be isolated from input context representation.

### [R06] When Correct Isn't Usable: Improving Structured Output Reliability in Small Language Models

**Source:** arXiv, May 2026 · **Workstream:** R10-A

[Publication / primary source](https://arxiv.org/abs/2605.02363)

Distinguishes semantic correctness from strict JSON output reliability on mathematics tasks. Supports separate syntax and semantic evaluation; does not establish ADR reliability.

### [R07] Mapping the Efficiency Landscape of Small Language Models

**Source:** IJCAI 2026 proceedings · **Workstream:** R10-A / R10-B

[Publication / primary source](https://ijcai.org/proceedings/2026/627)

Measures 75 small models across five tasks, considering performance and energy. Supports workload-dependent hardware/model selection and energy measurement.

### [R08] Cold Start Latency of Quantized Small Language Models on Serverless CPU Infrastructure

**Source:** Google Research publication record · **Workstream:** R10-B

[Publication / primary source](https://research.google/pubs/cold-start-latency-of-quantized-small-language-models-on-serverless-cpu-infrastructure/)

Benchmarks five models from 270M to 3.8B on Cloud Run CPU with GGUF quantization comparisons and memory tiers. Relevant to cold starts, utilization and CPU alternatives; not a Qwen3.5-4B ADR result.

### [R09] Scaling laws meet model architecture: Toward inference-efficient LLMs

**Source:** AWS AI Labs / Amazon Science, ICLR 2026 · **Workstream:** R10-B

[Publication / primary source](https://www.amazon.science/blog/making-llms-faster-without-sacrificing-accuracy)

Shows throughput can differ materially between similarly sized architectures; the reported maximum 47% throughput improvement is configuration-specific and not a monetary savings figure.

### [R10] FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance

**Source:** arXiv, May 2023 · **Workstream:** R10-B

[Publication / primary source](https://arxiv.org/abs/2305.05176)

Foundational cost-aware cascading and prompt adaptation; demonstrates that cascading is prior art.

### [R11] RouteLLM: Learning to Route LLMs with Preference Data

**Source:** arXiv, June 2024; revised February 2025 · **Workstream:** R10-B

[Publication / primary source](https://arxiv.org/abs/2406.18665)

Learned routing between stronger and weaker models. Reports more than twofold cost reduction in certain benchmarks at comparable quality; transfer to ADR governance must be evaluated.

### [R12] Speculative cascades — A hybrid approach for smarter, faster LLM inference

**Source:** Google Research, 2025 · **Workstream:** R10-B

[Publication / primary source](https://research.google/blog/speculative-cascades-a-hybrid-approach-for-smarter-faster-llm-inference/)

T5/Gemma experiments combine deferral and speculative decoding. Relevant alternative architecture; not equivalent to R10's request-level governance cascade.

### [R13] I know what I don't know: improving model cascades through confidence tuning

**Source:** Google Research, 2025 · **Workstream:** R10-B

[Publication / primary source](https://research.google/pubs/i-know-what-i-dont-know-improving-model-cascades-through-confidence-tuning/)

Gatekeeper calibrates deferral decisions. Motivates held-out routing calibration rather than reliance on raw self-reported confidence.

### [R14] Switchcraft: AI Model Router for Agentic Tool Calling

**Source:** Microsoft Research, 2026 · **Workstream:** R10-B

[Publication / primary source](https://www.microsoft.com/en-us/research/publication/switchcraft-ai-model-router-for-agentic-tool-calling/)

Agentic tool-call routing rather than chat-only routing. Compare against agent-aware alternatives; results on other tasks cannot substantiate R10 budget claims.

### [R15] Forge: Closing the Agentic Reliability Gap Between Self-Hosted and Frontier Language Models

**Source:** ACM conference proceedings, 2026 · **Workstream:** R10-A / R10-B

[Publication / primary source](https://doi.org/10.1145/3786335.3813193)

Investigates guardrails, tool-call recovery and serving backend effects in agentic workflows. Supports testing runtime and harness effects independently of parameter count.

### [R16] Effective context engineering for AI agents

**Source:** Anthropic engineering guidance, 2025 · **Workstream:** R10-A

[Publication / primary source](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents)

Practical context selection, compactness and tool design guidance. Practitioner evidence, not a controlled JSON-versus-JSONL result.

### [R17] How Claude Code is used in practice

**Source:** Anthropic research, 2026 · **Workstream:** R10-B

[Publication / primary source](https://www.anthropic.com/research/claude-code-expertise)

Empirical coding-agent session analysis. Useful for workload characterization; not a measurement of eligible architectural validation spend.

### [R18] From Requests to Sessions: A Large-Scale Characterization of Human-Driven Agentic Workloads

**Source:** Harvard Systems Group, 4 November 2026 · **Workstream:** R10-B

[Publication / primary source](https://systems.seas.harvard.edu/blog/agentic-traces-freeinference/)

Production coding-agent traffic analysis highlights growing context and session-level serving behavior. Motivates session-aware cost and caching metrics. Publication announcement identified; consult full paper before relying on numerical findings.

### [R19] Cut generative AI costs: Code for rules, models for judgment

**Source:** AWS technical guidance, 17 November 2026 · **Workstream:** R10-B

[Publication / primary source](https://aws.amazon.com/blogs/machine-learning/cut-generative-ai-costs-code-for-rules-models-for-judgment/)

Separates deterministic logic, constrained decisions and appropriately sized model calls. Closely related industrial guidance; not independent empirical verification of R10.

### [R20] Optimizing cost per task and proving agent ROI on Amazon Bedrock

**Source:** AWS technical guidance, 12 November 2026 · **Workstream:** R10-B

[Publication / primary source](https://aws.amazon.com/blogs/machine-learning/optimizing-cost-per-task-and-proving-agent-roi-on-amazon-bedrock/)

Cost attribution, observability and agent economics; reinforces task-level accounting and the need to include operational expenditure.

### [R21] Optimize AI economics on Amazon Bedrock with Accenture’s sequenced approach

**Source:** AWS / Accenture technical guidance, 19 November 2026 · **Workstream:** R10-B

[Publication / primary source](https://aws.amazon.com/blogs/machine-learning/optimize-ai-economics-on-amazon-bedrock-with-accentures-sequenced-approach/)

Enterprise cost optimization including routing and caching. Vendor-reported examples are context-specific, not an independent local-vs-cloud TCO baseline.

### [R22] Amazon Bedrock Intelligent Prompt Routing

**Source:** AWS product documentation · **Workstream:** R10-B

[Publication / primary source](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-routing.html)

Existing managed routing alternative. Benchmark against a relevant cloud-only budget/routed baseline, not just single premium-model calls.

### [R23] Agentic Inference for MLPerf Inference

**Source:** MLCommons, July 2026 · **Workstream:** R10-B

[Publication / primary source](https://mlcommons.org/2026/07/agentic-inference-for-mlperf-inference/)

Benchmark development for multi-turn agentic inference. Supports reporting workload shape, prefill, decode, caching and concurrency rather than a single tokens/s number.

### [R24] Qwen3.5-4B

**Source:** Qwen publisher model card · **Workstream:** R10-A

[Publication / primary source](https://huggingface.co/Qwen/Qwen3.5-4B)

Primary source for advertised base model benchmark results; not quantized EDH task measurements.

### [R25] Qwen3.5-4B-GGUF

**Source:** Unsloth model artifact card · **Workstream:** R10-A / R10-B

[Publication / primary source](https://huggingface.co/unsloth/Qwen3.5-4B-GGUF)

Artifact provenance and quantization variants; pin file revision/hash and independently measure runtime.

### [R26] OpenAI API pricing

**Source:** Provider rate card · **Workstream:** R10-B

[Publication / primary source](https://developers.openai.com/api/docs/pricing)

Dynamic rate source; capture dated regional/model/service-tier prices at experiment execution, including cached and billed reasoning tokens.

### [R27] Claude API pricing

**Source:** Provider rate card · **Workstream:** R10-B

[Publication / primary source](https://platform.claude.com/docs/en/about-claude/pricing)

Dynamic pricing source; compare budget and premium baselines and cache/batch discounts.

### [R28] AtomGradient Apple Silicon inference benchmark

**Source:** Community benchmark; source from original proposal · **Workstream:** R10-A / R10-B

[Publication / primary source](https://atomgradient.github.io/apple-silicon-llm-inference/)

Provisional quantization reference; exact benchmark configuration and reported values require independent verification before use.

## Suggested evidence extraction fields

Record title, authors, publication date/version, DOI/arXiv ID, venue and evidence type; task/dataset and sample size; models and exact quantization; context representation, token counts and retrieval; hardware/runtime/concurrency; metrics with uncertainty; pricing assumptions and complete cost denominator; threats to validity; applicability to R10; reproduction status. Keep observations from published sources separate from EDH measurements and synthetic business scenarios.

## Review protocol

Start from R03–R06 for context/ADR relevance, then R07–R15 for model efficiency and routing, and R16–R23 for production platform constraints. Revisit newer work before freezing the protocol. Record negative findings, deduplicate preprints and proceedings versions, and do not infer a research gap from this selected bibliography alone.
