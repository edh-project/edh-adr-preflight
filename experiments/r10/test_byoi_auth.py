import unittest
import hashlib
import hmac
from unittest.mock import patch
from byoi_auth import access_headers

class TestBYOIAuth(unittest.TestCase):
    def call(self, **overrides):
        args=dict(profile="macbook-local",provider="openai-compatible",
                  base="https://example.invalid/v1",suite="adr-only",repeats=1,
                  model="qwen4b",body=b'{"model":"qwen4b"}',
                  env={"R10_HMAC_KEY":"K"*40,"R10_API_KEY":"g"*43,
                       "R10_EXTERNAL_APPROVED":"true"})
        args.update(overrides)
        return access_headers(**args)
    def test_signature(self):
        with patch("byoi_auth.time.time",return_value=1700000000), patch("byoi_auth.secrets.token_hex",return_value="a"*32):
            h=self.call()
        self.assertEqual(h["X-R10-Timestamp"],"1700000000000")
        self.assertEqual(h["X-R10-Nonce"],"a"*32)
        msg="\n".join(("R10-HMAC-v2","1700000000000","a"*32,"POST","/v1/chat/completions",hashlib.sha256(b'{"model":"qwen4b"}').hexdigest(),hashlib.sha256(("Bearer "+"g"*43).encode()).hexdigest()))
        self.assertEqual(h["X-R10-Signature"],hmac.new(b"K"*40,msg.encode(),hashlib.sha256).hexdigest())
    def test_other_profiles(self):
        for profile in ("local","external-1","openai","anthropic"):
            self.assertEqual(self.call(profile=profile),{})
    def test_invalid_urls(self):
        for base in ("http://example.invalid/v1","https://example.invalid/v2",
                     "https://example.invalid:8443/v1","https://user@example.invalid/v1",
                     "https://example.invalid/v1?x=1","https://example.invalid/v1#x"):
            with self.subTest(base=base),self.assertRaises(ValueError): self.call(base=base)
    def test_scope(self):
        for override in ({"suite":"original-six"},{"repeats":2},{"model":"other"},{"provider":"anthropic"}):
            with self.subTest(override=override),self.assertRaises(ValueError): self.call(**override)
    def test_credentials_and_size(self):
        for env in ({"R10_HMAC_KEY":"short","R10_API_KEY":"g"*43,"R10_EXTERNAL_APPROVED":"true"},
                    {"R10_HMAC_KEY":"K"*40,"R10_API_KEY":"short","R10_EXTERNAL_APPROVED":"true"},
                    {"R10_HMAC_KEY":"K"*40,"R10_API_KEY":"g"*43}):
            with self.assertRaises(ValueError): self.call(env=env)
        with self.assertRaises(ValueError): self.call(body=b"x"*16385)
if __name__=="__main__": unittest.main()
