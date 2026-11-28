# R10 BYOI — Cloudflare Access-free HMAC candidate (NOT DEPLOYED)

Cloudflare Zero Trust Free onboarding requested a payment method on 2026-11-28.
This branch replaces Access with a **candidate** HMAC-SHA256 request-authentication
protocol. The production Worker remains unchanged until offline verification and
explicit deployment approval. No public route or tunnel should be enabled yet.

## Protocol

Only `POST /v1/chat/completions` with no query string is admitted. GitHub signs
the **exact UTF-8 request bytes** with a dedicated `R10_HMAC_KEY` secret:

```
message = "R10-HMAC-v2\n" + timestamp_ms + "\n" + nonce_hex_16_bytes +
          "\nPOST\n/v1/chat/completions\n" + sha256(body).hexdigest() + "\n" + sha256(("Bearer " + grant).encode()).hexdigest()
signature = hmac_sha256(key, message).hexdigest()
```

Headers: `X-R10-Timestamp`, `X-R10-Nonce`, `X-R10-Signature`.
The Worker validates the signature, +/-60-second clock window and
`R10_NOT_AFTER`, then atomically reserves a nonce in `R10NonceGate`.
The Durable Object enforces **at most nine admitted requests per deployed
object identity**, including requests that later fail at the gateway.
No bypass exists when the nonce store is unavailable. This is an intentionally
single-shot experiment; a fresh experiment requires a new gate identity
or an audited reset procedure. A fixed identity is used by default.

The gateway separately verifies `Authorization: Bearer <grant>`; the Worker
only forwards that header and the JSON body. Keep HMAC key and gateway grant
distinct, random, and stored only in secrets. The grant must be identical
to the token used by the local gateway process.

## Existing resources (do not recreate)

- Worker: `edh-r10-byoi-worker`
- Tunnel: `edh-r10-byoi-private` (inactive)
- Workers VPC service: `edh-r10-byoi-gateway`
- VPC service ID: `01a21d39-e39c-75a0-9bea-a82ad41879af`
- Binding: `PRIVATE_GATEWAY`; destination `localhost:8093`
- GitHub environment: `r10-macbook-local` (branch `main` only)
- Local gateway: `127.0.0.1:8093`; Qwen 4B: `127.0.0.1:8092`

## Required verification before any public HTTPS ingress

1. Run `python3 -m unittest discover -s experiments/r10 -p test_byoi_auth.py -v`
   and `node --test experiments/r10/byoi/worker.test.mjs`.
2. Verify the actual deployed Worker code and Durable Object migration/binding;
   check Cloudflare plan support and possible usage charges before deployment.
3. Set Worker secret `R10_HMAC_KEY` (>=32 ASCII characters) and Worker variable
   `R10_NOT_AFTER` (short future UTC ISO timestamp).
4. Set GitHub environment secrets `R10_HMAC_KEY` and `R10_API_KEY`, and
   variables `R10_EXTERNAL_APPROVED=true`, `R10_MODEL=qwen4b`, and
   `R10_URL=https://<approved-hostname>/v1`. Never echo values.
5. Verify the hostname's route maps exclusively to this Worker, test denial
   for unsigned, stale, tampered, duplicate and quota-exhausted requests.
6. Only then start the existing tunnel and dispatch the nine-case smoke test.
   Preserve negative tests, timestamps, response codes and provenance.
7. Disable the route and tunnel, expire `R10_NOT_AFTER`, revoke credentials.

**Caveat:** `workers_dev=false` in the example configuration intentionally
keeps ingress disabled; publishing a hostname requires a separately reviewed
route. This branch has not been deployed or validated end-to-end. The earlier
Access-based Worker remains the live deployment. No billing-free guarantee
is made for Durable Objects without verifying the account plan.
