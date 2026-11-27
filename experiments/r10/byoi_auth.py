"""Bounded Cloudflare Access authentication for the dedicated BYOI smoke profile."""
from urllib.parse import urlsplit

PROFILE = "macbook-local"

def access_headers(profile, provider, base, suite, repeats, model, env):
    """Do not return any credential for other execution profiles."""
    if profile != PROFILE:
        return {}
    u = urlsplit(base)
    if (u.scheme != "https" or not u.hostname or u.username or u.password
            or u.query or u.fragment or u.path != "/v1" or u.port not in (None, 443)):
        raise ValueError("BYOI requires approved HTTPS /v1 endpoint")
    if provider != "openai-compatible" or model != "qwen4b":
        raise ValueError("BYOI smoke requires the Qwen 4B compatible gateway")
    if suite != "adr-only" or repeats != 1:
        raise ValueError("BYOI smoke is limited to nine requests")
    if env.get("R10_EXTERNAL_APPROVED") != "true":
        raise ValueError("BYOI external dispatch not approved")
    names = ("CF_ACCESS_CLIENT_ID", "CF_ACCESS_CLIENT_SECRET", "R10_API_KEY")
    values = [env.get(n, "") for n in names]
    if any(not v or any(c.isspace() for c in v) for v in values):
        raise ValueError("Missing or invalid BYOI credential configuration")
    return {"CF-Access-Client-Id": values[0],
            "CF-Access-Client-Secret": values[1]}
