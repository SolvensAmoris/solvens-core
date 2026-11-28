"""Regression tests for the security remediation branch."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from security.audit import AuditLogger, AuditEventType
from security.pii_redaction import PIICategory, PIIRedactor
from security.rbac import Permission, RBACManager, Role
from cosmos.visualizer.dag_renderer import DAGGraph, DAGNode, DAGEdge, DAGRenderer, NodeType


class PIIRemediationTests(unittest.TestCase):
    def test_generic_and_aws_api_keys_are_both_detected(self):
        redactor = PIIRedactor()
        generic = "sk_" + ("a" * 28)
        aws = "AKIA" + ("1" * 16)
        found = [m.value for m in redactor.detect("generic " + generic + " and AWS " + aws) if m.category == PIICategory.API_KEY]
        self.assertIn(generic, found)
        self.assertIn(aws, found)

    def test_nested_list_payload_is_redacted_without_mutating_input(self):
        redactor = PIIRedactor()
        secret = "sk_" + ("a" * 28)
        original = {"content": [{"text": "contact a@example.com"}, ["key=" + secret]]}
        cleaned, matches = redactor.redact_dict(original)
        self.assertNotIn("a@example.com", str(cleaned))
        self.assertNotIn(secret, str(cleaned))
        self.assertGreaterEqual(len(matches), 2)
        self.assertIn("a@example.com", str(original))


class RBACTestTests(unittest.TestCase):
    def test_role_map_imports_and_editor_has_run_permission(self):
        from security.rbac import ROLE_PERMISSIONS
        self.assertIn(Permission.WORKFLOW_RUN, ROLE_PERMISSIONS[Role.EDITOR])

    def test_admin_cannot_cross_tenant_workflow_acl(self):
        manager = RBACManager()
        owner = manager.create_user("owner@example.test", "tenant-a", Role.OWNER)
        manager.set_workflow_acl("foreign-workflow", "tenant-b", public=True)
        self.assertFalse(manager.can_run_workflow(owner, "foreign-workflow"))


class AuditChainTests(unittest.TestCase):
    def test_chain_verifies_and_detects_metadata_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / "audit.sqlite")
            logger = AuditLogger(db)
            logger.log(
                event_type=AuditEventType.USER_LOGIN,
                actor_id="u1",
                actor_type="user",
                team_id="t1",
                resource_type="session",
                resource_id="s1",
                action="login",
                metadata={"source": "test"},
            )
            valid, errors = logger.verify_chain()
            self.assertTrue(valid, errors)
            with sqlite3.connect(db) as conn:
                conn.execute("UPDATE audit_events SET metadata = ?", ('{"source":"tampered"}',))
            valid, errors = logger.verify_chain()
            self.assertFalse(valid)
            self.assertTrue(any("hash mismatch" in error for error in errors))


class RendererSecurityTests(unittest.TestCase):
    def test_svg_and_html_escape_untrusted_labels(self):
        graph = DAGGraph(
            metadata={"name": "<script>alert(1)</script>"},
            nodes=[DAGNode("n1", "<img src=x onerror=alert(1)>", NodeType.TASK)],
            edges=[DAGEdge("n1", "n1", "<svg onload=alert(1)>")],
        )
        renderer = DAGRenderer()
        svg = renderer.render_svg(graph)
        html = renderer.render_html(graph)
        self.assertNotIn("<script>alert(1)</script>", svg)
        self.assertNotIn("<img src=x", svg)
        self.assertNotIn("<svg onload=", svg)
        self.assertNotIn("<script>alert(1)</script>", html)


if __name__ == "__main__":
    unittest.main()
