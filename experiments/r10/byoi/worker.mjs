// R10 private VPC transport. No generic proxy, no public model port.
const PATH = "/v1/chat/completions";
const TARGET = "http://localhost" + PATH;
const REQUEST_LIMIT = 16384;
const RESPONSE_LIMIT = 65536;
const MAX_SKEW_MS = 60000;
const enc = new TextEncoder();
const hex = bytes => Array.from(new Uint8Array(bytes), b => b.toString(16).padStart(2,"0")).join("");
const isHex = s => /^[a-f0-9]{64}$/.test(s);
async function mac(secret, message) {
  const key = await crypto.subtle.importKey("raw", enc.encode(secret), {name:"HMAC", hash:"SHA-256"}, false, ["sign"]);
  return hex(await crypto.subtle.sign("HMAC", key, enc.encode(message)));
}
const headers = {"Content-Type": "application/json", "Cache-Control": "no-store"};
const fail = (status, error) => new Response(JSON.stringify({error}), {status, headers});

async function bounded(stream, limit) {
  if (!stream) return new Uint8Array();
  const reader = stream.getReader();
  const chunks = [];
  let size = 0;
  try {
    for (;;) {
      const {done, value} = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > limit) {
        await reader.cancel();
        throw new RangeError("body limit");
      }
      chunks.push(value);
    }
    const result = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) {
      result.set(chunk, offset);
      offset += chunk.byteLength;
    }
    return result;
  } finally { reader.releaseLock(); }
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname !== PATH || url.search) return fail(404, "route denied");
    if (request.method !== "POST") return fail(405, "method denied");
    // Billing-independent admission: signed, short-lived request + independent gateway grant.
    // Do not enable a public route until the signed-request tests and secret provisioning pass.
    const deadline = Date.parse(env.R10_NOT_AFTER || "");
    if (!env.R10_HMAC_KEY || env.R10_HMAC_KEY.length < 32 || !env.R10_NONCES ||
        !Number.isFinite(deadline) || Date.now() >= deadline)
      return fail(503, "admission closed");
    const ts = request.headers.get("X-R10-Timestamp") || "";
    const nonce = request.headers.get("X-R10-Nonce") || "";
    const sig = request.headers.get("X-R10-Signature") || "";
    if (!/^\d{13}$/.test(ts) || !/^[a-f0-9]{32}$/.test(nonce) || !isHex(sig))
      return fail(403, "signature required");
    const now = Date.now();
    if (Math.abs(now - Number(ts)) > MAX_SKEW_MS || Number(ts) >= deadline)
      return fail(403, "signature expired");
    const auth = request.headers.get("Authorization") || "";
    if (!/^Bearer [A-Za-z0-9_-]{32,128}$/.test(auth)) return fail(401, "grant required");
    if (request.headers.get("Content-Type")?.split(";")[0].trim().toLowerCase() !== "application/json")
      return fail(415, "content type denied");
    const length = request.headers.get("Content-Length");
    if (length !== null && (!/^\d+$/.test(length) || Number(length) > REQUEST_LIMIT))
      return fail(413, "body limit");
    let body;
    try { body = await bounded(request.body, REQUEST_LIMIT); }
    catch { return fail(413, "body limit"); }
    if (!body.byteLength || Date.now() >= deadline) return fail(400, "request denied");
    const digest = hex(await crypto.subtle.digest("SHA-256", body));
    const grantDigest = hex(await crypto.subtle.digest("SHA-256", enc.encode(auth)));
    const signed = ["R10-HMAC-v2", ts, nonce, "POST", PATH, digest, grantDigest].join("\n");
    const expected = await mac(env.R10_HMAC_KEY, signed);
    // Constant-time comparison of fixed-length ASCII digests.
    let diff = 0;
    for (let i=0;i<64;i++) diff |= expected.charCodeAt(i) ^ sig.charCodeAt(i);
    if (diff !== 0) return fail(403, "signature invalid");
    // A single Durable Object serializes nonce admission and the total request quota.
    // Failure to reach it closes admission; never silently skip replay protection.
    try {
      const id = env.R10_NONCES.idFromName("r10-byoi-one-shot");
      const gate = await env.R10_NONCES.get(id).fetch("https://internal/admit", {
        method: "POST", headers: {"Content-Type":"application/json"},
        body: JSON.stringify({nonce, deadline})
      });
      if (!gate.ok) return fail(gate.status === 409 ? 409 : 429, "replay or quota denied");
    } catch { return fail(503, "replay protection unavailable"); }
    try {
      const response = await env.PRIVATE_GATEWAY.fetch(TARGET, {
        method: "POST", redirect: "manual",
        headers: {"Content-Type": "application/json", "Authorization": auth},
        body,
        signal: AbortSignal.timeout(75000)
      });
      if (response.status !== 200) {
        const status = [400,401,403,404,405,413,429].includes(response.status)
          ? response.status : 502;
        if (response.body) await response.body.cancel();
        return fail(status, "gateway denied or unavailable");
      }
      const raw = await bounded(response.body, RESPONSE_LIMIT);
      return new Response(raw, {status: 200, headers});
    } catch { return fail(502, "private transport unavailable"); }
  }
};

export class R10NonceGate {
  constructor(state) { this.state = state; }
  async fetch(request) {
    if (request.method !== "POST" || new URL(request.url).pathname !== "/admit")
      return fail(404, "route denied");
    let data;
    try { data = await request.json(); } catch { return fail(400, "invalid admission"); }
    if (!/^[a-f0-9]{32}$/.test(data?.nonce || "") ||
        !Number.isFinite(data?.deadline) || Date.now() >= data.deadline)
      return fail(403, "admission expired");
    return this.state.storage.transaction(async tx => {
      const seen = await tx.get("nonce:" + data.nonce);
      if (seen) return fail(409, "replay denied");
      const count = (await tx.get("count")) || 0;
      if (count >= 9) return fail(429, "quota exceeded");
      await tx.put("nonce:" + data.nonce, true);
      await tx.put("count", count + 1);
      return new Response(null, {status: 204});
    });
  }
}
