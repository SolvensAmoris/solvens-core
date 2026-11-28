"""OIDC validation regression tests using a local RSA key; no network IdP required."""
import os
import unittest
import time
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from security import oidc


class _SigningKey:
    def __init__(self, key):
        self.key = key


class _FakeJwks:
    def __init__(self, key):
        self.key = key

    def get_signing_key_from_jwt(self, token):
        return _SigningKey(self.key)


class OIDCValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.public_key = cls.private_key.public_key()

    def setUp(self):
        self.env = patch.dict(os.environ, {
            "SOLVENS_OIDC_ISSUER": "https://id.example.test/",
            "SOLVENS_OIDC_AUDIENCE": "solvens-api",
            "SOLVENS_OIDC_JWKS_URI": "https://id.example.test/.well-known/jwks.json",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        oidc._jwks_client.cache_clear()
        self.jwks_patch = patch("security.oidc._jwks_client", return_value=_FakeJwks(self.public_key))
        self.jwks_patch.start()
        self.addCleanup(self.jwks_patch.stop)

    def _token(self, **overrides):
        claims = {
            "sub": "user-123",
            "tenant_id": "tenant-a",
            "roles": ["developer"],
            "iss": "https://id.example.test/",
            "aud": "solvens-api",
            "iat": int(time.time()),
            "exp": int(time.time()) + 600,
        }
        claims.update(overrides)
        return jwt.encode(claims, self.private_key, algorithm="RS256")

    def test_valid_token_returns_verified_principal(self):
        principal = oidc.verify_access_token(self._token(email="dev@example.test"))
        self.assertEqual(principal.subject, "user-123")
        self.assertEqual(principal.tenant_id, "tenant-a")
        self.assertEqual(principal.roles, frozenset({"developer"}))

    def test_missing_tenant_claim_is_rejected(self):
        with self.assertRaises(PermissionError):
            oidc.verify_access_token(self._token(tenant_id=None))

    def test_wrong_audience_is_rejected(self):
        with self.assertRaises(PermissionError):
            oidc.verify_access_token(self._token(aud="another-api"))

    def test_wrong_issuer_is_rejected(self):
        with self.assertRaises(PermissionError):
            oidc.verify_access_token(self._token(iss="https://attacker.example/"))

    def test_untrusted_role_string_shape_is_rejected(self):
        with self.assertRaises(PermissionError):
            oidc.verify_access_token(self._token(roles={"admin": True}))


if __name__ == "__main__":
    unittest.main()
