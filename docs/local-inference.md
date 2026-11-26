# Run the ADR preflight on a developer Mac

The local runner starts a temporary loopback `llama-server` for each reviewer invoked by the preflight. It loads one GGUF at a time and stops the server after the review. The existing fail-closed review policy determines the outcome. Use a checkout with the [live adapter fix](https://github.com/edh-project/edh-adr-preflight/pull/5).

| Role | GGUF expected under `~/models` |
| --- | --- |
| Primary | `Qwen3.8-27B/Qwen3.8-27B-UD-Q5_K_XL.gguf` |
| Independent | `Gemma4-31B/gemma-4-31B-it-qat-UD-Q4_K_XL.gguf` |
| Optional triage | `Qwen3.5-4B/Qwen3.5-4B-UD-Q5_K_XL.gguf` |

## Download the optional 4B model

The pinned Unsloth text GGUF is 3.25 GB. One file is sufficient for text ADRs. [Model file and SHA-256](https://huggingface.co/unsloth/Qwen3.5-4B-GGUF/blob/e87f176479d0855a907a41277aca2f8ee7a09523/Qwen3.5-4B-UD-Q5_K_XL.gguf)

```sh
hf download unsloth/Qwen3.5-4B-GGUF Qwen3.5-4B-UD-Q5_K_XL.gguf \
  --revision e87f176479d0855a907a41277aca2f8ee7a09523 \
  --local-dir "$HOME/models/Qwen3.5-4B"

printf '%s  %s\n' \
  b4c36a8e14a80c21bcab5a067ce342b2e70e28f60b4aa95ad12203fa17b87426 \
  "$HOME/models/Qwen3.5-4B/Qwen3.5-4B-UD-Q5_K_XL.gguf" | shasum -a 256 -c -
```

## Run locally

From a clean checkout containing this runner, with Python 3.10+ and `llama-server` on `PATH`:

```sh
edh_run_dir=$(mktemp -d)
python3 local_preflight.py --output "$edh_run_dir"
```

Use `--cases conflict incomplete` for a shorter run that exercises semantic escalation and deterministic rejection. Add `--triage` to include 4B. The runner prints each case decision, writes detailed per-case JSON and local llama-server logs, and produces `evidence.json`. A completed run can contain `REVIEW`, `REJECT` or reviewer errors. Inspect `evidence.json` and the case files for those outcomes.

The manifest contains each model's role, file name, quant, byte size and SHA-256, the provider-reported model alias when it matches the launch alias, timing and tokens, the runtime version and settings, and the Git revision and hashes of the policy and source ADRs. Logs and full model responses stay in the local run directory.

## Submit a finished run to GitHub

Once `adr-local-evidence.yml` is on `main`, submit `evidence.json` from a run on public synthetic test cases:

```sh
gh workflow run adr-local-evidence.yml --repo edh-project/edh-adr-preflight --ref main \
  -F "evidence=@$edh_run_dir/evidence.json"
```

The GitHub-hosted job validates the manifest and checks the policy and fixture hashes against the stated Git revision. It creates an Actions summary and artifact with developer-reported runtime and model provenance. The Mac connects outbound to GitHub once the run finishes. This workflow receives the summary JSON and verifies public Git blobs. Runtime and model provenance are supplied by the developer's machine.

## Use 4B for the JSON versus JSONL pilot

[Experiment 001](https://github.com/edh-project/edh-adr-preflight/pull/2) has a separate paired harness. It varies input and output serialization while keeping the cases, model and decoding budget constant. Start the downloaded 4B on loopback in one terminal:

```sh
llama-server --host 127.0.0.1 --port 8082 --ctx-size 8192 --parallel 1 \
  --n-gpu-layers 99 --reasoning-budget 256 --alias Qwen3.5-4B-UD-Q5_K_XL \
  --model "$HOME/models/Qwen3.5-4B/Qwen3.5-4B-UD-Q5_K_XL.gguf"
```

In another terminal, from a checkout of Experiment 001:

```sh
edh_jsonl_run=$(mktemp -d)
ADR_PRIMARY_URL=http://127.0.0.1:8082/v1 \
  ADR_PRIMARY_MODEL=Qwen3.5-4B-UD-Q5_K_XL ADR_TIMEOUT_SECONDS=180 \
  python3 benchmark_jsonl.py --mode live --repeats 1 --output "$edh_jsonl_run"
```

One repeat exercises 12 requests. Use `--repeats 3` for the 36-request pilot. The benchmark writes `trials.jsonl`, `comparison.json` and `summary.md` for the paired results.
