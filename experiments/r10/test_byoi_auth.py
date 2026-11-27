import unittest
from byoi_auth import access_headers

class TestBYOIAuth(unittest.TestCase):
    def call(self, **overrides):
        args = dict(profile="macbook-local", provider="openai-compatible",
                    base="https://example.invalid/v1", suite="adr-only",
                    repeats=1, model="qwen4b",
                    env={"CF_ACCESS_CLIENT_ID":"test-id",
                         "CF_ACCESS_CLIENT_SECRET":"test-value",
                         "R10_API_KEY":"test-grant",
                         "R10_EXTERNAL_APPROVED":"true"})
        args.update(overrides)
        return access_headers(**args)
    def test_headers(self):
        self.assertEqual(self.call(), {"CF-Access-Client-Id":"test-id",
                                       "CF-Access-Client-Secret":"test-value"})
    def test_other_profiles(self):
        for profile in ("local", "external-1", "openai", "anthropic"):
            self.assertEqual(self.call(profile=profile), {})
    def test_reject_invalid_urls(self):
        for base in ("http://example.invalid/v1", "https://example.invalid/v2",
                     "https://example.invalid:8443/v1", "https://user@example.invalid/v1",
                     "https://example.invalid/v1?x=1", "https://example.invalid/v1#x"):
            with self.subTest(base=base), self.assertRaises(ValueError):
                self.call(base=base)
    def test_require_all_credentials(self):
        for missing in ("CF_ACCESS_CLIENT_ID", "CF_ACCESS_CLIENT_SECRET", "R10_API_KEY", "R10_EXTERNAL_APPROVED"):
            env={"CF_ACCESS_CLIENT_ID":"test-id","CF_ACCESS_CLIENT_SECRET":"test-value",
                 "R10_API_KEY":"test-grant","R10_EXTERNAL_APPROVED":"true"}
            del env[missing]
            with self.subTest(missing=missing), self.assertRaises(ValueError):
                self.call(env=env)
    def test_bound_scope(self):
        for override in ({"suite":"original-six"},{"repeats":2},{"model":"other"},
                         {"provider":"anthropic"}):
            with self.subTest(override=override), self.assertRaises(ValueError):
                self.call(**override)
if __name__ == "__main__": unittest.main()
