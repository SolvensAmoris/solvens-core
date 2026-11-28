"""Adversarial security regression tests for RBAC, PII, and audit integrity."""
import asyncio
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

from security.rbac import APIKey, RBACManager, Role, User
from security.pii_redaction import PIIAwareLLMWrapper
from security.audit import AuditLogger, AuditEventType


class FakeLLM:
    async def chat(self, messages):
        self.messages = messages
        return {"ok": True}

    def chat_sync(self, messages):
        self.messages = messages
        return {"ok": True}


class RBACAdversarialTests(unittest.TestCase):
    def setUp(self):
        self.manager = RBACManager()
        self.user = self.manager.create_user("dev@example.test", "tenant-a", Role.DEVELOPER)

    def test_forged_user_cannot_mint_owner_jwt(self):
        forged = User(
            id=self.user.id, email=self.user.email,
            team_id=self.user.team_id, role=Role.OWNER,
        )
        with self.assertRaises((ValueError, PermissionError)):
            self.manager.generate_token(forged)

    def test_revoked_cached_api_key_object_is_rejected(self):
        key, raw = self.manager.create_api_key(self.user.id, "ci", ["workflow:run"])
        self.assertTrue(self.manager.api_key_can_access(key, "workflow", "run"))
        self.manager.revoke_api_key(key.id)
        self.assertFalse(self.manager.api_key_can_access(key, "workflow", "run"))

    def test_expired_cached_api_key_object_is_rejected(self):
        key, _ = self.manager.create_api_key(self.user.id, "ci", ["admin:*"])
        key.expires_at = datetime.utcnow() - timedelta(seconds=1)
        self.assertFalse(self.manager.api_key_can_access(key, "workflow", "delete"))

    def test_api_key_cannot_be_bound_to_another_tenant(self):
        with self.assertRaises((ValueError, PermissionError)):
            self.manager.create_api_key(
                self.user.id, "cross-tenant", ["admin:*"], team_id="tenant-b"
            )

    def test_token_validation_rejects_deleted_or_changed_identity(self):
        import os
        old = os.environ.get("SOLVENS_SECRET_KEY")
        os.environ["SOLVENS_SECRET_KEY"] = "test-only-secret-long-enough"
        try:
            token = self.manager.generate_token(self.user)
            self.manager._users[self.user.id].role = Role.VIEWER
            self.assertIsNone(self.manager.validate_token(token))
        finally:
            if old is None:
                os.environ.pop("SOLVENS_SECRET_KEY", None)
            else:
                os.environ["SOLVENS_SECRET_KEY"] = old


class PIIAdversarialTests(unittest.TestCase):
    def test_all_roles_and_message_fields_are_redacted(self):
        llm = FakeLLM()
        wrapper = PIIAwareLLMWrapper(llm)
        secret = "sk_" + "z" * 28
        messages = [
            {"role": "system", "content": "system email admin@example.com"},
            {"role": "developer", "content": "developer key " + secret},
            {"role": "assistant", "content": [{"type": "text", "text": "reply user@example.com"}],
             "metadata": {"credential": secret}},
            {"role": "tool", "content": {"result": ["contact ops@example.com"]}},
        ]
        wrapper.chat_sync(messages)
        serialized = repr(llm.messages)
        for value in ("admin@example.com", secret, "user@example.com", "ops@example.com"):
            self.assertNotIn(value, serialized)
        self.assertEqual(messages[0]["content"], "system email admin@example.com")


class AuditAdversarialTests(unittest.TestCase):
    def _log(self, logger, index):
        return logger.log(
            event_type=AuditEventType.USER_LOGIN, actor_id=f"u{index}",
            actor_type="user", team_id="t1", resource_type="session",
            resource_id=f"s{index}", action="login", metadata={"n": index},
        )

    def test_concurrent_writers_produce_one_valid_linear_chain(self):
        with tempfile.TemporaryDirectory() as directory:
            logger = AuditLogger(str(Path(directory) / "audit.sqlite"))
            with ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(lambda i: self._log(logger, i), range(40)))
            valid, errors = logger.verify_chain()
            self.assertTrue(valid, errors)
            self.assertEqual(len(logger.query(limit=100)), 40)

    def test_tampering_with_signed_event_fields_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / "audit.sqlite")
            logger = AuditLogger(db)
            self._log(logger, 1)
            with sqlite3.connect(db) as conn:
                conn.execute("UPDATE audit_events SET actor_id='attacker'")
            valid, errors = logger.verify_chain()
            self.assertFalse(valid)
            self.assertTrue(errors)
