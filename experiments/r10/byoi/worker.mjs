// R10 private VPC transport. No generic proxy, no public model port.
const PATH = "/v1/chat/completions";
const TARGET = "http://localhost" + PATH;
const REQUEST_LIMIT = 16384;
const RESPONSE_LIMIT = 65536;
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
    // The platform supplies ctx.access only after Access authentication.
    // No caller-supplied identity header is a substitute.
    const deadline = Date.parse(env.R10_NOT_AFTER || "");
    if (!env.POLICY_AUD || !Number.isFinite(deadline) ||
        Date.now() >= deadline) return fail(503, "admission closed");
    if (!ctx?.access || ctx.access.aud !== env.POLICY_AUD)
      return fail(403, "Access required");
    // The Access application must contain ONLY the dedicated Service Auth rule.
    // Gateway verifies this independent short-lived grant before any inference.
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
