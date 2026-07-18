"""
Billing & Usage Tiers

Monetization layer that ties limits to pricing tiers.
"""

import os
import time
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional
import asyncio

logger = logging.getLogger("cosmos.billing")


class PlanTier(Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


@dataclass
class TierConfig:
    """Configuration for a pricing tier."""
    name: str
    max_concurrent: int
    rate_limit: int  # per minute
    rate_window: float  # seconds
    queue_maxsize: int
    monthly_limit: int  # tasks per month (0 = unlimited)
    price_monthly: float
    price_yearly: float
    features: list[str]


# Tier configurations
TIER_CONFIGS = {
    PlanTier.FREE: TierConfig(
        name="Free",
        max_concurrent=5,
        rate_limit=20,
        rate_window=60.0,
        queue_maxsize=100,
        monthly_limit=100,
        price_monthly=0,
        price_yearly=0,
        features=[
            "Core engine",
            "Local execution",
            "100 tasks/month",
            "Community support",
        ],
    ),
    PlanTier.PRO: TierConfig(
        name="Pro",
        max_concurrent=20,
        rate_limit=300,
        rate_window=60.0,
        queue_maxsize=1000,
        monthly_limit=0,  # unlimited
        price_monthly=49,
        price_yearly=470,  # ~20% discount
        features=[
            "Everything in Free",
            "Cloud execution",
            "Analytics dashboard",
            "Priority support",
            "5 team members",
            "API access",
            "Unlimited tasks",
        ],
    ),
    PlanTier.ENTERPRISE: TierConfig(
        name="Enterprise",
        max_concurrent=100,
        rate_limit=2000,
        rate_window=60.0,
        queue_maxsize=5000,
        monthly_limit=0,  # unlimited
        price_monthly=299,
        price_yearly=2870,
        features=[
            "Everything in Pro",
            "Unlimited team",
            "SLA guarantee",
            "Custom integrations",
            "Dedicated support",
            "On-premise option",
            "SSO/SAML",
        ],
    ),
}


class UsageTracker:
    """
    Track usage per user for billing.
    """
    
    def __init__(self):
        self._usage: dict[str, dict] = {}
        self._lock = asyncio.Lock()
    
    async def record_run(
        self,
        user_id: str,
        tier: PlanTier,
        duration_ms: float,
        tokens_used: int = 0,
        cost: float = 0.0,
    ):
        """Record a run for billing."""
        async with self._lock:
            if user_id not in self._usage:
                self._usage[user_id] = {
                    "tier": tier,
                    "runs": 0,
                    "tokens": 0,
                    "cost": 0.0,
                    "duration_ms": 0,
                    "period_start": time.time(),
                }
            
            u = self._usage[user_id]
            u["runs"] += 1
            u["tokens"] += tokens_used
            u["cost"] += cost
            u["duration_ms"] += duration_ms
            
            logger.info(
                f"Usage: user={user_id}, tier={tier.value}, "
                f"runs={u['runs']}, cost=${u['cost']:.4f}"
            )
    
    async def check_limit(self, user_id: str, tier: PlanTier) -> tuple[bool, str]:
        """
        Check if user is within their tier limits.
        
        Returns (allowed, reason)
        """
        async with self._lock:
            config = TIER_CONFIGS[tier]
            
            if user_id not in self._usage:
                return True, "First run"
            
            u = self._usage[user_id]
            
            # Check monthly limit
            if config.monthly_limit > 0 and u["runs"] >= config.monthly_limit:
                return False, f"Monthly limit reached ({config.monthly_limit} tasks)"
            
            return True, "OK"
    
    def get_usage(self, user_id: str) -> Optional[dict]:
        """Get usage stats for a user."""
        return self._usage.get(user_id)


class BillingMiddleware:
    """
    Middleware that enforces tier limits before scheduling.
    """
    
    def __init__(self, usage_tracker: Optional[UsageTracker] = None):
        self.usage_tracker = usage_tracker or UsageTracker()
        self._tier_cache: dict[str, PlanTier] = {}
    
    def get_tier_for_user(self, user_id: str) -> PlanTier:
        """
        Get tier for a user. In production, this would query the database.
        
        For MVP: use cache or default to FREE.
        """
        if user_id in self._tier_cache:
            return self._tier_cache[user_id]
        return PlanTier.FREE
    
    def set_tier_for_user(self, user_id: str, tier: PlanTier):
        """Set tier for a user."""
        self._tier_cache[user_id] = tier
        logger.info(f"User {user_id} tier set to {tier.value}")
    
    def get_config_for_user(self, user_id: str) -> TierConfig:
        """Get tier config for a user."""
        tier = self.get_tier_for_user(user_id)
        return TIER_CONFIGS[tier]
    
    async def check_and_record(
        self,
        user_id: str,
        tier: PlanTier,
        duration_ms: float,
        tokens_used: int = 0,
        cost: float = 0.0,
    ) -> tuple[bool, str, Optional[TierConfig]]:
        """
        Check limits and record usage.
        
        Returns (allowed, reason, config)
        """
        # Check limit
        allowed, reason = await self.usage_tracker.check_limit(user_id, tier)
        
        if not allowed:
            return False, reason, TIER_CONFIGS[tier]
        
        # Record usage
        await self.usage_tracker.record_run(
            user_id=user_id,
            tier=tier,
            duration_ms=duration_ms,
            tokens_used=tokens_used,
            cost=cost,
        )
        
        return True, "OK", TIER_CONFIGS[tier]
    
    def create_scheduler_config(self, user_id: str) -> dict:
        """
        Create scheduler config for a user based on their tier.
        """
        config = self.get_config_for_user(user_id)
        
        return {
            "max_concurrent": config.max_concurrent,
            "rate_limit": config.rate_limit,
            "rate_window": config.rate_window,
            "queue_maxsize": config.queue_maxsize,
            "circuit_failure_threshold": 5,
            "circuit_recovery_timeout": 30.0,
            "retry_max_attempts": 3,
            "retry_base_delay": 1.0,
            "upscale_warning_threshold": 0.8,
        }


# Global instances
_usage_tracker: Optional[UsageTracker] = None
_billing_middleware: Optional[BillingMiddleware] = None


def get_usage_tracker() -> UsageTracker:
    global _usage_tracker
    if _usage_tracker is None:
        _usage_tracker = UsageTracker()
    return _usage_tracker


def get_billing_middleware() -> BillingMiddleware:
    global _billing_middleware
    if _billing_middleware is None:
        _billing_middleware = BillingMiddleware(get_usage_tracker())
    return _billing_middleware
