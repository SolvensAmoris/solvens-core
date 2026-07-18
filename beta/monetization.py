"""
Monetization - Stripe Integration Stub

MOCK implementation for MVP.
Replace with real Stripe integration when ready.
"""

import uuid
import time
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class Plan(Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


@dataclass
class Subscription:
    plan: Plan
    customer_id: str
    subscription_id: str
    status: str  # active, cancelled, past_due
    current_period_end: float
    created_at: float


@dataclass
class CheckoutSession:
    url: str
    session_id: str


class StripeMock:
    """
    Mock Stripe integration for MVP.
    
    For production:
    1. Install stripe: pip install stripe
    2. Set STRIPE_SECRET_KEY env var
    3. Replace this with real implementation
    """
    
    PRICES = {
        Plan.PRO: {
            "monthly": 4900,  # $49.00 in cents
            "name": "Cosmos Engine Pro",
        },
        Plan.ENTERPRISE: {
            "monthly": 29900,  # $299.00 in cents
            "name": "Cosmos Engine Enterprise",
        },
    }
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self._subscriptions = {}
        self._customers = {}
    
    def create_customer(self, email: str, name: str = "") -> str:
        """Create a customer."""
        customer_id = f"cus_{uuid.uuid4().hex[:14]}"
        self._customers[customer_id] = {
            "email": email,
            "name": name,
            "created": time.time(),
        }
        return customer_id
    
    def create_checkout_session(
        self,
        customer_id: str,
        plan: Plan,
        success_url: str = "https://cosmosengine.ai/success",
        cancel_url: str = "https://cosmosengine.ai/pricing",
    ) -> CheckoutSession:
        """
        Create a Stripe checkout session.
        
        MOCK: Returns fake URL. Replace with real Stripe API call.
        """
        if plan == Plan.FREE:
            raise ValueError("Free plan doesn't need checkout")
        
        session_id = f"cs_{uuid.uuid4().hex[:24]}"
        
        # MOCK: Generate fake checkout URL
        price = self.PRICES[plan]
        url = f"https://checkout.stripe.com/mock/{session_id}?plan={plan.value}&price={price['monthly']}"
        
        return CheckoutSession(url=url, session_id=session_id)
    
    def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """Get subscription details."""
        return self._subscriptions.get(subscription_id)
    
    def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancel a subscription."""
        if subscription_id in self._subscriptions:
            self._subscriptions[subscription_id]["status"] = "cancelled"
            return True
        return False
    
    def create_webhook_event(self, payload: str, signature: str) -> dict:
        """
        Verify and parse webhook event.
        
        MOCK: Returns mock event.
        """
        # MOCK: Return mock event
        return {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": f"cs_{uuid.uuid4().hex[:24]}",
                    "status": "complete",
                }
            }
        }


# Global instance
_stripe: Optional[StripeMock] = None


def get_stripe() -> StripeMock:
    global _stripe
    if _stripe is None:
        import os
        api_key = os.getenv("STRIPE_SECRET_KEY")
        _stripe = StripeMock(api_key)
    return _stripe


def create_pro_checkout(email: str) -> CheckoutSession:
    """Convenience: Create Pro plan checkout."""
    stripe = get_stripe()
    customer = stripe.create_customer(email)
    return stripe.create_checkout_session(customer, Plan.PRO)


def create_enterprise_checkout(email: str) -> CheckoutSession:
    """Convenience: Create Enterprise plan checkout."""
    stripe = get_stripe()
    customer = stripe.create_customer(email)
    return stripe.create_checkout_session(customer, Plan.ENTERPRISE)
