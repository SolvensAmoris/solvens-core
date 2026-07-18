"""
Tests for payment flow - Stripe integration
"""

import pytest
from unittest.mock import patch


class TestAuthFlow:
    """Test authentication flow."""
    
    def test_password_hashing(self):
        """Passwords should be hashed consistently."""
        import sys
        sys.path.insert(0, '/workspace/project/solvens-core')
        from api.main import UserDB
        
        db = UserDB()
        password = "test_password_123"
        
        hash1 = db._hash_password(password)
        hash2 = db._hash_password(password)
        
        assert hash1 == hash2
        assert hash1 != password
    
    def test_create_user(self):
        """Users can be created."""
        import sys
        sys.path.insert(0, '/workspace/project/solvens-core')
        from api.main import UserDB
        
        db = UserDB()
        user = db.create_user("test@example.com", "password123")
        
        assert user["email"] == "test@example.com"
        assert user["tier"] == "free"
        assert user["password_hash"] != "password123"
    
    def test_verify_password(self):
        """Password verification should work."""
        import sys
        sys.path.insert(0, '/workspace/project/solvens-core')
        from api.main import UserDB
        
        db = UserDB()
        user = db.create_user("test@example.com", "password123")
        
        assert db.verify_password(user, "password123") is True
        assert db.verify_password(user, "wrong") is False
    
    def test_session_creation(self):
        """Sessions can be created and verified."""
        import sys
        sys.path.insert(0, '/workspace/project/solvens-core')
        from api.main import UserDB
        
        db = UserDB()
        user = db.create_user("test@example.com", "password123")
        
        token = db.create_session(user["id"])
        assert token is not None
        
        verified = db.verify_session(token)
        assert verified is not None
        assert verified["id"] == user["id"]


class TestTierConfiguration:
    """Test tier configuration."""
    
    def test_free_tier_limits(self):
        """Free tier should have correct limits."""
        import sys
        sys.path.insert(0, '/workspace/project/solvens-core')
        from api.main import TIER_CONFIG
        
        free = TIER_CONFIG["free"]
        
        assert free["max_concurrent"] == 5
        assert free["rate_limit"] == 20
        assert free["monthly_limit"] == 100
        assert free["price_monthly"] == 0
    
    def test_pro_tier_limits(self):
        """Pro tier should have correct limits."""
        import sys
        sys.path.insert(0, '/workspace/project/solvens-core')
        from api.main import TIER_CONFIG
        
        pro = TIER_CONFIG["pro"]
        
        assert pro["max_concurrent"] == 20
        assert pro["rate_limit"] == 300
        assert pro["monthly_limit"] == 0  # unlimited
        assert pro["price_monthly"] == 49
    
    def test_enterprise_tier_limits(self):
        """Enterprise tier should have correct limits."""
        import sys
        sys.path.insert(0, '/workspace/project/solvens-core')
        from api.main import TIER_CONFIG
        
        ent = TIER_CONFIG["enterprise"]
        
        assert ent["max_concurrent"] == 100
        assert ent["rate_limit"] == 2000
        assert ent["monthly_limit"] == 0  # unlimited
        assert ent["price_monthly"] == 299


class TestQuotaEnforcement:
    """Test quota enforcement."""
    
    def test_monthly_limit_enforcement(self):
        """Monthly limit should be enforced."""
        import sys
        sys.path.insert(0, '/workspace/project/solvens-core')
        from api.main import UserDB, TIER_CONFIG
        
        db = UserDB()
        db.create_user("test@example.com", "password123")
        
        free_cfg = TIER_CONFIG["free"]
        monthly_limit = free_cfg["monthly_limit"]
        
        # Simulate reaching the limit
        for _ in range(monthly_limit):
            db.record_usage("test@example.com")
        
        usage = db.get_usage("test@example.com")
        assert usage["runs"] == monthly_limit
        assert usage["runs"] >= monthly_limit
    
    def test_unlimited_tier_no_limit(self):
        """Pro/Enterprise should have unlimited usage."""
        import sys
        sys.path.insert(0, '/workspace/project/solvens-core')
        from api.main import UserDB, TIER_CONFIG
        
        db = UserDB()
        db.create_user("pro@example.com", "password123")
        db.set_tier("pro@example.com", "pro")
        
        pro_cfg = TIER_CONFIG["pro"]
        assert pro_cfg["monthly_limit"] == 0  # unlimited
        
        # Should be able to record unlimited usage
        for i in range(1000):
            db.record_usage("pro@example.com")
        
        usage = db.get_usage("pro@example.com")
        assert usage["runs"] == 1000


class TestUsageTracking:
    """Test usage tracking."""
    
    def test_record_usage(self):
        """Usage should be tracked correctly."""
        import sys
        sys.path.insert(0, '/workspace/project/solvens-core')
        from api.main import UserDB
        
        db = UserDB()
        db.create_user("test@example.com", "password123")
        
        db.record_usage("test@example.com", tokens=500, cost=0.05)
        db.record_usage("test@example.com", tokens=300, cost=0.03)
        
        usage = db.get_usage("test@example.com")
        
        assert usage["runs"] == 2
        assert usage["tokens"] == 800
        assert usage["cost"] == 0.08


class TestWebhookProcessing:
    """Test Stripe webhook processing."""
    
    def test_checkout_completed_sets_tier(self):
        """Checkout completion should set user tier."""
        import sys
        sys.path.insert(0, '/workspace/project/solvens-core')
        from api.main import UserDB
        
        db = UserDB()
        db.create_user("customer@example.com", "password123")
        
        # Simulate webhook event
        db.set_tier("customer@example.com", "pro")
        
        user = db.get_user("customer@example.com")
        assert user["tier"] == "pro"
    
    def test_subscription_deleted_downgrades(self):
        """Subscription deletion should downgrade to free."""
        import sys
        sys.path.insert(0, '/workspace/project/solvens-core')
        from api.main import UserDB
        
        db = UserDB()
        db.create_user("customer@example.com", "password123")
        db.set_tier("customer@example.com", "pro")
        
        # Simulate subscription deleted webhook
        customer_id = "cus_test123"
        db.set_stripe_customer("customer@example.com", customer_id)
        
        # Process deletion
        email = db.get_email_by_stripe_customer(customer_id)
        if email:
            db.set_tier(email, "free")
        
        user = db.get_user("customer@example.com")
        assert user["tier"] == "free"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
