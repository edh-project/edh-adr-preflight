"""Signed R10 BYOI admission. Only for the bounded macbook-local profile."""
import hashlib
import hmac
import secrets
import time
from urllib.parse import urlsplit

PROFILE = "macbook-local"
PATH = "/v1/chat/completions"

def access_headers(profile, provider, base, suite, repeats, model, env, body=None):
    if profile != PROFILE:
        return {}
    u = urlsplit(base)
    if (u.scheme != "https" or not u.hostname or u.username or u.password
            or u.query or u.fragment or u.path != "/v1" or u.port not in (None, 443)):
        raise ValueError("BYOI requires approved HTTPS /v1 endpoint")
    if provider != "openai-compatible" or model != "qwen4b":
        raise ValueError("BYOI requires Qwen 4B compatible gateway")
    if suite != "adr-only" or repeats != 1 or env.get("R10_EXTERNAL_APPROVED") != "true":
        raise ValueError("BYOI is restricted to nine approved requests")
    key = env.get("R10_HMAC_KEY", "")
    grant = env.get("R10_API_KEY", "")
    if (len(key) < 32 or not (32 <= len(grant) <= 128)
            or not all(c.isalnum() or c in "_-" for c in grant)
            or any(ord(c) > 127 for c in key)):
        raise ValueError("Missing or invalid BYOI credentials")
    if body is None:
        return {}
    if not isinstance(body, bytes) or len(body) > 16384:
        raise ValueError("Invalid signed request body")
    timestamp = str(int(time.time() * 1000))
    nonce = secrets.token_hex(16)
    digest = hashlib.sha256(body).hexdigest()
    grant_digest = hashlib.sha256(("Bearer " + grant).encode()).hexdigest()
    message = "\n".join(("R10-HMAC-v2", timestamp, nonce, "POST", PATH, digest, grant_digest))
    signature = hmac.new(key.encode(), message.encode(), hashlib.sha256).hexdigest()
    return {"X-R10-Timestamp": timestamp, "X-R10-Nonce": nonce,
            "X-R10-Signature": signature}
