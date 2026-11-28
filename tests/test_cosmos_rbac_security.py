"""Adversarial tests for the primary Cosmos RBAC implementation."""
import os
import unittest

from cosmos.security.rbac import RBAC, Permission, PermissionDenied, Role, User, WorkflowACL


class CosmosRBACSecurityTests(unittest.TestCase):
    def setUp(self):
        os.environ["SOLVENS_RBAC_BOOTSTRAP_TOKEN"] = "test-bootstrap-secret"
        self.rbac = RBAC(secret_key="s" * 40)
        self.team = self.rbac.create_team("tenant-a", bootstrap_token="test-bootstrap-secret")
        self.owner = self.rbac.create_user(
            "owner@example.test", self.team.id, Role.OWNER,
            bootstrap_token="test-bootstrap-secret",
        )
        self.developer = self.rbac.create_user(
            "developer@example.test", self.team.id, Role.DEVELOPER,
            actor_id=self.owner.id,
        )

    def test_user_creation_requires_bootstrap_or_tenant_admin(self):
        with self.assertRaises(PermissionDenied):
            self.rbac.create_user("intruder@example.test", self.team.id, Role.DEVELOPER)

    def test_admin_cannot_assign_owner(self):
        admin = self.rbac.create_user(
            "admin@example.test", self.team.id, Role.ADMIN, actor_id=self.owner.id
        )
        with self.assertRaises(PermissionDenied):
            self.rbac.create_user(
                "new-owner@example.test", self.team.id, Role.OWNER, actor_id=admin.id
            )

    def test_acl_mutation_cannot_cross_tenant(self):
        with self.assertRaises(PermissionDenied):
            self.rbac.set_workflow_acl(
                "foreign-flow", "tenant-b", is_public=True, actor_id=self.owner.id
            )

    def test_owner_cannot_bypass_foreign_tenant_acl(self):
        self.assertFalse(self.rbac.can_run_workflow(self.owner, "missing-flow"))
        self.rbac._workflow_acls["foreign-flow"] = WorkflowACL(
            "foreign-flow", "tenant-b", is_public=True
        )
        self.assertFalse(self.rbac.can_run_workflow(self.owner, "foreign-flow"))

    def test_developer_cannot_issue_admin_api_key(self):
        with self.assertRaises(PermissionDenied):
            self.rbac.create_api_key(
                user_id=self.developer.id,
                name="escalation",
                scopes=["admin:*"],
                actor_id=self.developer.id,
            )

    def test_api_key_owner_can_create_only_permitted_scopes(self):
        key, _ = self.rbac.create_api_key(
            user_id=self.developer.id,
            name="ci",
            scopes=["workflow:run"],
            actor_id=self.developer.id,
        )
        self.assertTrue(self.rbac.api_key_can_access(key, "workflow", "run"))
        self.assertFalse(self.rbac.api_key_can_access(key, "workflow", "delete"))

    def test_jwt_requires_configured_secret_and_current_identity(self):
        token = self.rbac.generate_token(self.developer)
        self.assertIsNotNone(self.rbac.validate_token(token))
        self.rbac._users[self.developer.id].role = Role.VIEWER
        self.assertIsNone(self.rbac.validate_token(token))

    def test_forged_user_cannot_pass_permission_check(self):
        forged = User(
            id=self.developer.id,
            email=self.developer.email,
            team_id=self.developer.team_id,
            role=Role.OWNER,
        )
        self.assertFalse(self.rbac.check_permission(forged, Permission.USER_MANAGE))


if __name__ == "__main__":
    unittest.main()
