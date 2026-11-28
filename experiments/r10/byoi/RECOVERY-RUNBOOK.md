# EDH R10 BYOI — Disaster Recovery and Operator Runbook

**Updated:** 2026-11-28. **Status:** partially deployed, NOT end-to-end verified. This file intentionally contains **no credentials**. It is the durable handoff for a replacement Mac, lost disk, or lost ChatGPT session. Do not treat historical timestamps, paths, or statuses as current.

## Architecture and resource inventory

```text
GitHub Actions (r10-benchmark.yml; environment r10-macbook-local)
  POST HTTPS /v1/chat/completions, HMAC v2 + Bearer
    -> Cloudflare Worker edh-r10-byoi-worker
       -> Durable Object R10NonceGate (nonce replay and 9-admission quota)
       -> PRIVATE_GATEWAY VPC Service (HTTP localhost:8093)
       -> existing Cloudflare Tunnel edh-r10-byoi-private
       -> Mac gateway.py bound 127.0.0.1:8093
       -> local llama.cpp Qwen3.5-4B bound 127.0.0.1:8092
```

- Repository: https://github.com/edh-project/edh-adr-preflight
- PR #10 branch: `experiment/r10-byoi-access-smoke`.
- Worker: `edh-r10-byoi-worker`; Cloudflare account ID `37cfceb9bfb0fa822746c398070e8d1e`.
- Tunnel: `edh-r10-byoi-private`; ID `a5798f68-ff35-414c-b121-f4e99bc8ffcd`. Existing remotely managed tunnel; **do not recreate or rotate token by default**.
- VPC Service: `edh-r10-byoi-gateway`, ID `01a21d39-e39c-75a0-9bea-a82ad41879af`, HTTP host `localhost`, port `8093`. Worker binding `PRIVATE_GATEWAY`.
- Durable Object class `R10NonceGate`, binding `R10_NONCES`, migration tag `r10-nonce-v1`.
- Diagnostic gate ID `r10-byoi-diagnostic-v1`; benchmark gate ID `r10-byoi-one-shot`. Both are persistent and independently capped at nine *admitted* requests. Changing the ID does not reset the counter.
- GitHub environment: `r10-macbook-local`; experimental branch allowed in deployment branch policy (verified manually 2026-11-28).
- Last *verified live* Worker version before gate-isolation redeploy: `d4c66239-ab24-475d-8950-302de9695d98`, 2026-11-28T17:36Z. Gate isolation code committed to PR #10 but NOT YET DEPLOYED at this checkpoint.
- Cloudflare Workers production and preview workers.dev URLs were OFF, no custom domain/route as last verified. Tunnel has one configured route, which does **not** mean Worker has public HTTPS ingress.
- Local machine was Mac M2 Max, macOS 14, Homebrew, Python 3, Node, gh CLI, Wrangler via `npx --yes wrangler@4`, `cloudflared 2026.11.2`.
- Qwen3.5-4B GGUF: `Qwen3.5-4B-UD-Q5_K_XL.gguf`; historical SHA-256 `b4c36a8e14a80c21bcab5a067ce342b2e70e28f60b4aa95ad12203fa17b87426`. Verify model file independently after recovery. llama.cpp server uses port 8092; exact original llama-server flags/model path need to be recovered from machine-specific configuration or reconstructed and tested, **not guessed**.
- Historical gateway directory (NOT backed up by this repo): `~/WORK/_edh/edh-4b-jsonl-pilot/gateway.DvjNfX/`, with `gateway.py`, `dataset.json`, `test_gateway.py`. **Back up these three files to an authorized private, encrypted location before disk loss.** The repo contains R10 dataset and runner, but do not assume it contains identical gateway implementation.
- Temporary deployment directory `/var/folders/p3/ydjk_m194wn_ffc9zhkqm1xh0000gn/T/edh-r10-deploy.YnMwJm` was ephemeral. **Never depend on it for disaster recovery.** Clone repository afresh.

## Credentials: source of truth and lost-disk recovery

| Name | Location | Handling |
|---|---|---|
| `R10_HMAC_KEY` | Cloudflare Worker secret; GitHub environment secret; historical local file `~/.config/edh/r10/hmac.key` (0600) | 96 ASCII hex characters generated once via `openssl rand -hex 48`. Neither Cloudflare nor GitHub returns existing secret values. If local file is lost, **rotate** to a fresh shared key in BOTH locations; do not pretend to recover old value. |
| `R10_API_KEY` | GitHub environment secret | Same bearer value as local gateway `R10_GATEWAY_TOKEN`; no need to put bearer secret in Worker. If lost, rotate and restart gateway and replace GitHub secret. |
| `R10_GATEWAY_TOKEN` | Mac gateway process environment (historically recoverable via `ps eww` while process was running) | Never print or paste into chat. Process environment is **not a backup** and disappears on disk loss/restart. Recover from secure store or rotate. |
| Tunnel connector token | Cloudflare Zero Trust Dashboard, existing Tunnel → connector setup / Add replica | Treat as secret. Do not paste into shell history or repo. Use hidden prompt and `cloudflared tunnel run --token "$TUNNEL_TOKEN"`. Do not rotate unless necessary. |
| `R10_NOT_AFTER` | Cloudflare Worker secret | UTC ISO deadline. Historical value `2026-11-28T18:36:02.257574Z` **expires**; configure a new short future deadline immediately before controlled testing. |
| `R10_GATE_ID` | Cloudflare Worker secret or variable | Must be explicitly set to diagnostic or benchmark value after isolation deployment; missing/unknown fails closed. |
| `R10_EXTERNAL_APPROVED`, `R10_MODEL`, `R10_URL` | GitHub environment variables | `true`, `qwen4b`, and `https://<approved-Worker-hostname>/v1` respectively. **Hostname not yet provisioned/verified.** |

**Security:** Secrets must not enter public commits, issues, Wiki pages, screenshots, command-line arguments visible in process lists, or terminal history. A locally saved secret with `0600` permissions is still lost when the disk is lost: back it up in an encrypted secrets manager with recovery access, or be prepared to rotate. `wrangler secret list --name edh-r10-byoi-worker` shows names only.

## Recovery from a blank Mac (do not rely on four terminals)

1. Install prerequisites: Homebrew (if needed), `cloudflared`, Python 3, Node, `gh`; authenticate `gh auth login` and `npx --yes wrangler@4 login`. Verify account/permissions. On macOS 14, Homebrew built cloudflared and Go from source; install may take minutes and may prompt.
2. Clone `edh-project/edh-adr-preflight` and checkout `experiment/r10-byoi-access-smoke`; inspect PR #10 and latest commit before deploying. `cd experiments/r10/byoi` for Wrangler. Never trust stale temporary paths.
3. Restore the private gateway files, GGUF and exact llama.cpp configuration from independent backups. Verify checksums and tests. Start llama.cpp on `127.0.0.1:8092` using verified model/settings. Check `curl --noproxy '*' -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8092/v1/models` returns 200.
4. Restore/rotate `R10_GATEWAY_TOKEN` securely, then start gateway with token **in its process environment**: `python3 gateway.py --port 8093 --ttl 900 --limit 18`. It blocks the terminal by design; use a dedicated tab/session or supervised service, **not** an arbitrary shell-killing command. GET `/v1/chat/completions` previously returned HTTP 405 (expected for unsupported method), showing port is listening; does NOT prove inference. Unit tests: `python3 -m unittest test_gateway.py -v` (historically 9/9 PASS).
5. Start **existing** remotely managed tunnel via Cloudflare Dashboard's connector token. `cloudflared tunnel list` requires `cert.pem` and failed even when token-based tunnel worked; **do not infer the tunnel is missing**. On a secure terminal, `read -rs "TUNNEL_TOKEN?Tunnel token: "; printf '\n'; cloudflared tunnel run --token "$TUNNEL_TOKEN"; unset TUNNEL_TOKEN` (the last command runs only after the foreground tunnel exits; use separate tab). Four `Registered tunnel connection` logs were observed on 2026-11-28; this proves connector ↔ Cloudflare, NOT VPC ↔ gateway.
6. Inspect `worker.mjs` and `wrangler.jsonc`; run `node --test worker.test.mjs` and `python3 -m unittest discover -s ../ -p test_byoi_auth.py -v` from the BYOI folder (or use repository root commands below). Deploy **once** after verified source: `CLOUDFLARE_ACCOUNT_ID=37cfceb9bfb0fa822746c398070e8d1e npx --yes wrangler@4 deploy` from `experiments/r10/byoi`. `wrangler versions upload` failed with pending DO migration; `wrangler deploy` succeeded. Verify `wrangler deployments list --name edh-r10-byoi-worker`. Deploying a Worker does **not** necessarily create public ingress.
7. Provision/rotate Worker HMAC secret and GitHub HMAC secret from the **same** local secure key; do not create separate keys. Example from `experiments/r10/byoi`: `npx --yes wrangler@4 secret put R10_HMAC_KEY < "$HOME/.config/edh/r10/hmac.key"`; `gh secret set R10_HMAC_KEY --repo edh-project/edh-adr-preflight --env r10-macbook-local < "$HOME/.config/edh/r10/hmac.key"`. Set GitHub bearer via `printf '%s' "$R10_GATEWAY_TOKEN" | gh secret set R10_API_KEY --repo edh-project/edh-adr-preflight --env r10-macbook-local` **only from the shell where token exists**. Never echo values.
8. Set Worker `R10_GATE_ID=r10-byoi-diagnostic-v1` (using `wrangler secret put` with stdin), and short UTC `R10_NOT_AFTER` before diagnostic admission. Worker must fail closed until these are set. Reconfigure after expiry; never assume an old deadline is valid.
9. **Ingress is a separate approval step:** current `workers_dev=false`; no Worker public route. Choose one temporary HTTPS hostname routed exclusively to this Worker, with HMAC v2, strict deadline and bounded quotas. Verify route/host and account billing implications. Do not publish localhost/model port or a generic tunnel route. Without reachable Worker HTTPS endpoint, GitHub-hosted Actions cannot run E2E.
10. Perform negative tests first (unsigned 403, invalid path 404, invalid method 405, expired 503); these should not consume DO quota. Then a **single** signed diagnostic request to exercise actual DO and VPC, followed by exact nonce replay expecting 409 (no extra admission). Record status and sanitized traces. A signed request reserves admission **before** gateway fetch: gateway errors still consume diagnostic quota. Do not use the benchmark gate during diagnostics.
11. Before benchmark, change Worker `R10_GATE_ID=r10-byoi-one-shot` and verify fresh, unconsumed benchmark gate; renew deadline, restart gateway if its TTL expired. Configure GitHub environment vars: `R10_EXTERNAL_APPROVED=true`, `R10_MODEL=qwen4b`, `R10_URL=https://<Worker-host>/v1`. Workflow inputs: `mode=external-api`, `external_profile=macbook-local`, `suite=adr-only`, `repeats=1`, `authorize_nonfree=true`; branch `experiment/r10-byoi-access-smoke`. **Verify workflow_dispatch availability on default branch before running**; environment branch allowlist alone does not guarantee dispatch. `runner.py` writes `trials.jsonl`, `comparison.json`, `provenance.json` under `reports/r10`; artifact upload step must be verified. Runner may exit nonzero if any result invalid; this is experimental evidence, not necessarily transport failure.
12. After experiment, disable temporary Worker ingress, stop tunnel and gateway gracefully, expire/revoke credentials and verify no public access. Archive sanitized evidence and commit a status update; do not commit credentials.

## Verified timeline / outstanding work

- 2026-11-28: Qwen 8092 `GET /v1/models` HTTP 200. Gateway unit tests 9/9 PASS and live GET port 8093 HTTP 405.
- `cloudflared 2026.11.2` installed; existing Tunnel established four QUIC connections; connectivity pre-check DNS/UDP/TCP/API PASS.
- Cloudflare Worker deployed HMAC v2 + DO binding + VPC binding, active version `d4c66239-ab24-475d-8950-302de9695d98`. `wrangler secret list` initially `[]`; then HMAC key and deadline uploaded successfully.
- GitHub environment secrets `R10_HMAC_KEY` and `R10_API_KEY` uploaded successfully; no values in repository.
- PR #10 updated with gate isolation and regression tests; **not yet deployed**.
- A staging command failed: `node --check worker.mjs.next` on Node v24 yielded `ERR_UNKNOWN_FILE_EXTENSION`. This was a **staging filename bug**, not a Worker syntax failure. Correct validation: `node --check worker.mjs` for actual .mjs, or `node --input-type=module --check < worker.mjs.next` for staged file via stdin. Do not deploy until staged source is verified.
- Not yet verified: actual DO runtime persistence, Worker public ingress, VPC Service → Mac gateway, successful inference through tunnel, GitHub workflow dispatch and nine-trial artifact.
- **Operational caveat:** gateway `--ttl 900` expires 15 minutes after startup; start/restart it immediately before tests. Model may remain running. Historical `R10_NOT_AFTER` also expires.
- **Do not run `set -e`, `exec`, or commands that replace/terminate interactive shell.** Guard diagnostics separately from fatal failures. Do not assume archives extracted.

## Quick commands from repository root

```bash
python3 -m unittest discover -s experiments/r10 -p test_byoi_auth.py -v
node --test experiments/r10/byoi/worker.test.mjs
node --check experiments/r10/byoi/worker.mjs
gh secret list --repo edh-project/edh-adr-preflight --env r10-macbook-local
CLOUDFLARE_ACCOUNT_ID=37cfceb9bfb0fa822746c398070e8d1e npx --yes wrangler@4 secret list --name edh-r10-byoi-worker
CLOUDFLARE_ACCOUNT_ID=37cfceb9bfb0fa822746c398070e8d1e npx --yes wrangler@4 deployments list --name edh-r10-byoi-worker
```

**Remaining gap for truly disk-independent recovery:** gateway source and exact llama.cpp launch flags/model GGUF are not established as backed up in this repository; copy to a private recoverable store with appropriate permissions, document checksum and restore procedure. Public repo/wiki must not contain live tokens.
