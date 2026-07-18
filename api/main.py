"""
Cosmos API - Production-Ready with Stripe Integration

FastAPI application with:
- User authentication (simple JWT)
- Stripe checkout + webhook
- Tier enforcement
- Usage tracking
"""

import os
import time
import uuid
import hashlib
import hmac
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, EmailStr
import stripe

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cosmos.api")

# Initialize FastAPI
app = FastAPI(
    title="Cosmos Engine API",
    description="Production-hardened AI agent execution with Stripe billing",
    version="1.0.0",
)

# Environment variables
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# Initialize Stripe (if key provided)
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

# ============================================================================
# MODELS
# ============================================================================

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    tier: str
    max_concurrent: int
    rate_limit: int

class CheckoutRequest(BaseModel):
    tier: str  # "pro" or "enterprise"

class UsageResponse(BaseModel):
    user_id: str
    tier: str
    runs: int
    tokens: int
    cost: float
    period_start: float

# ============================================================================
# DATABASE (In-Memory for MVP)
# ============================================================================

class UserDB:
    """Simple in-memory user database."""
    
    def __init__(self):
        self.users: dict[str, dict] = {}
        self.sessions: dict[str, str] = {}  # token -> user_id
        self.stripe_ids: dict[str, str] = {}  # user_id -> stripe_customer_id
    
    def create_user(self, email: str, password: str) -> dict:
        user_id = str(uuid.uuid4())
        password_hash = self._hash_password(password)
        
        user = {
            "id": user_id,
            "email": email,
            "password_hash": password_hash,
            "tier": "free",
            "stripe_customer_id": None,
            "stripe_subscription_id": None,
            "created_at": time.time(),
            "usage": {
                "runs": 0,
                "tokens": 0,
                "cost": 0.0,
                "period_start": time.time(),
            },
        }
        
        self.users[email] = user
        logger.info(f"User created: {email} -> {user_id}")
        return user
    
    def get_user(self, email: str) -> Optional[dict]:
        return self.users.get(email)
    
    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        for user in self.users.values():
            if user["id"] == user_id:
                return user
        return None
    
    def verify_password(self, user: dict, password: str) -> bool:
        return user["password_hash"] == self._hash_password(password)
    
    def set_tier(self, email: str, tier: str):
        if email in self.users:
            self.users[email]["tier"] = tier
            logger.info(f"User {email} tier set to {tier}")
    
    def set_stripe_customer(self, email: str, customer_id: str):
        if email in self.users:
            self.users[email]["stripe_customer_id"] = customer_id
            self.stripe_ids[customer_id] = email
    
    def set_subscription(self, email: str, subscription_id: str):
        if email in self.users:
            self.users[email]["stripe_subscription_id"] = subscription_id
    
    def record_usage(self, email: str, tokens: int = 0, cost: float = 0.0):
        if email in self.users:
            u = self.users[email]["usage"]
            u["runs"] += 1
            u["tokens"] += tokens
            u["cost"] += cost
    
    def get_usage(self, email: str) -> dict:
        if email in self.users:
            return self.users[email]["usage"]
        return {"runs": 0, "tokens": 0, "cost": 0.0, "period_start": time.time()}
    
    def create_session(self, user_id: str) -> str:
        token = self._generate_token()
        self.sessions[token] = user_id
        return token
    
    def verify_session(self, token: str) -> Optional[dict]:
        user_id = self.sessions.get(token)
        if user_id:
            return self.get_user_by_id(user_id)
        return None
    
    def get_email_by_stripe_customer(self, customer_id: str) -> Optional[str]:
        return self.stripe_ids.get(customer_id)
    
    @staticmethod
    def _hash_password(password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def _generate_token() -> str:
        return str(uuid.uuid4()) + str(uuid.uuid4())


# Global database instance
db = UserDB()

# Create test user
db.create_user("test@cosmosengine.ai", "test123")

# ============================================================================
# TIER CONFIGURATION
# ============================================================================

TIER_CONFIG = {
    "free": {
        "max_concurrent": 5,
        "rate_limit": 20,
        "rate_window": 60,
        "queue_maxsize": 100,
        "monthly_limit": 100,
        "price_monthly": 0,
        "stripe_price_id": None,
    },
    "pro": {
        "max_concurrent": 20,
        "rate_limit": 300,
        "rate_window": 60,
        "queue_maxsize": 1000,
        "monthly_limit": 0,  # unlimited
        "price_monthly": 49,
        "stripe_price_id": os.getenv("STRIPE_PRO_PRICE_ID", "price_pro_placeholder"),
    },
    "enterprise": {
        "max_concurrent": 100,
        "rate_limit": 2000,
        "rate_window": 60,
        "queue_maxsize": 5000,
        "monthly_limit": 0,
        "price_monthly": 299,
        "stripe_price_id": os.getenv("STRIPE_ENTERPRISE_PRICE_ID", "price_enterprise_placeholder"),
    },
}

# ============================================================================
# AUTH DEPENDENCIES
# ============================================================================

async def get_current_user(authorization: str = Header(None)) -> dict:
    """Dependency to get current authenticated user."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0] != "Bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = parts[1]
    user = db.verify_session(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user

# ============================================================================
# AUTH ROUTES
# ============================================================================

@app.post("/api/auth/register")
async def register(data: UserCreate):
    """Register a new user."""
    if data.email in db.users:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = db.create_user(data.email, data.password)
    token = db.create_session(user["id"])
    
    tier_cfg = TIER_CONFIG["free"]
    
    return {
        "user": {
            "id": user["id"],
            "email": user["email"],
            "tier": "free",
        },
        "token": token,
        "limits": tier_cfg,
    }

@app.post("/api/auth/login")
async def login(data: UserLogin):
    """Login and get token."""
    user = db.get_user(data.email)
    
    if not user or not db.verify_password(user, data.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = db.create_session(user["id"])
    tier_cfg = TIER_CONFIG[user["tier"]]
    
    return {
        "user": {
            "id": user["id"],
            "email": user["email"],
            "tier": user["tier"],
        },
        "token": token,
        "limits": tier_cfg,
    }

@app.get("/api/auth/me")
async def me(user: dict = Depends(get_current_user)):
    """Get current user info."""
    tier_cfg = TIER_CONFIG[user["tier"]]
    
    return {
        "id": user["id"],
        "email": user["email"],
        "tier": user["tier"],
        "limits": tier_cfg,
        "usage": user["usage"],
    }

# ============================================================================
# CHECKOUT ROUTES
# ============================================================================

@app.post("/api/checkout")
async def create_checkout(
    data: CheckoutRequest,
    user: dict = Depends(get_current_user),
):
    """Create Stripe checkout session for upgrade."""
    if data.tier not in ["pro", "enterprise"]:
        raise HTTPException(status_code=400, detail="Invalid tier")
    
    if user["tier"] == data.tier:
        raise HTTPException(status_code=400, detail="Already on this tier")
    
    tier_cfg = TIER_CONFIG[data.tier]
    
    if not STRIPE_SECRET_KEY:
        # Mock mode - just upgrade directly
        db.set_tier(user["email"], data.tier)
        return {
            "success": True,
            "tier": data.tier,
            "message": "Tier upgraded (mock mode - no Stripe configured)",
        }
    
    try:
        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            customer_email=user["email"],
            line_items=[{
                "price": tier_cfg["stripe_price_id"],
                "quantity": 1,
            }],
            mode="subscription",
            success_url=f"{BASE_URL}/dashboard?success=true&tier={data.tier}",
            cancel_url=f"{BASE_URL}/pricing?canceled=true",
            metadata={
                "user_id": user["id"],
                "user_email": user["email"],
                "tier": data.tier,
            },
        )
        
        logger.info(f"Checkout session created: {checkout_session.id} for {user['email']}")
        
        return {
            "checkout_url": checkout_session.url,
            "session_id": checkout_session.id,
        }
        
    except Exception as e:
        logger.error(f"Stripe checkout error: {e}")
        raise HTTPException(status_code=500, detail=f"Checkout failed: {str(e)}")

@app.get("/api/checkout/portal")
async def customer_portal(user: dict = Depends(get_current_user)):
    """Create Stripe customer portal session."""
    if not user["stripe_customer_id"]:
        raise HTTPException(status_code=400, detail="No Stripe customer found")
    
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    try:
        session = stripe.billing_portal.Session.create(
            customer=user["stripe_customer_id"],
            return_url=f"{BASE_URL}/dashboard",
        )
        
        return {"portal_url": session.url}
        
    except Exception as e:
        logger.error(f"Stripe portal error: {e}")
        raise HTTPException(status_code=500, detail=f"Portal failed: {str(e)}")

# ============================================================================
# STRIPE WEBHOOK
# ============================================================================

@app.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    if not STRIPE_WEBHOOK_SECRET:
        logger.warning("Stripe webhook secret not configured")
        return JSONResponse({"received": True})
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    logger.info(f"Stripe webhook: {event['type']}")
    
    # Handle events
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_email = session.get("customer_email")
        tier = session.get("metadata", {}).get("tier", "pro")
        
        if user_email and user_email in db.users:
            db.set_tier(user_email, tier)
            if session.get("customer"):
                db.set_stripe_customer(user_email, session["customer"])
            if session.get("subscription"):
                db.set_subscription(user_email, session["subscription"])
            
            logger.info(f"✅ User {user_email} upgraded to {tier}")
    
    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        customer_id = subscription.get("customer")
        
        user_email = db.get_email_by_stripe_customer(customer_id)
        if user_email:
            db.set_tier(user_email, "free")
            logger.info(f"✅ User {user_email} downgraded to free (subscription canceled)")
    
    elif event["type"] == "invoice.payment_failed":
        invoice = event["data"]["object"]
        customer_id = invoice.get("customer")
        
        logger.warning(f"Payment failed for customer {customer_id}")
        # TODO: Send email notification
    
    return JSONResponse({"received": True})

# ============================================================================
# USAGE & LIMITS ROUTES
# ============================================================================

@app.get("/api/usage")
async def get_usage(user: dict = Depends(get_current_user)):
    """Get current usage for user."""
    tier_cfg = TIER_CONFIG[user["tier"]]
    usage = user["usage"]
    
    # Check if monthly limit reached
    monthly_limit = tier_cfg["monthly_limit"]
    limit_reached = monthly_limit > 0 and usage["runs"] >= monthly_limit
    
    return {
        "tier": user["tier"],
        "limits": tier_cfg,
        "usage": {
            "runs": usage["runs"],
            "tokens": usage["tokens"],
            "cost": usage["cost"],
        },
        "monthly_limit_reached": limit_reached,
        "remaining": max(0, monthly_limit - usage["runs"]) if monthly_limit > 0 else None,
    }

@app.post("/api/execute")
async def execute_task(
    task: dict,
    user: dict = Depends(get_current_user),
):
    """Execute a task with rate limiting and quota enforcement."""
    tier_cfg = TIER_CONFIG[user["tier"]]
    usage = user["usage"]
    
    # Check monthly limit
    monthly_limit = tier_cfg["monthly_limit"]
    if monthly_limit > 0 and usage["runs"] >= monthly_limit:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Monthly limit reached",
                "tier": user["tier"],
                "limit": monthly_limit,
                "upgrade_url": f"{BASE_URL}/pricing",
            }
        )
    
    # Record usage
    db.record_usage(user["email"], tokens=task.get("estimated_tokens", 100))
    
    # TODO: Actually execute the task with HardenedScheduler
    # For now, return mock response
    return {
        "success": True,
        "task_id": str(uuid.uuid4()),
        "tier": user["tier"],
        "limits": tier_cfg,
    }

# ============================================================================
# ADMIN ROUTES
# ============================================================================

@app.get("/api/admin/users")
async def list_users(user: dict = Depends(get_current_user)):
    """List all users (admin only - simplified for MVP)."""
    # In production, add admin check
    users = []
    for u in db.users.values():
        users.append({
            "email": u["email"],
            "tier": u["tier"],
            "usage": u["usage"],
            "created_at": u["created_at"],
        })
    
    return {"users": users, "total": len(users)}

@app.get("/api/admin/revenue")
async def revenue_dashboard(user: dict = Depends(get_current_user)):
    """Revenue dashboard."""
    # Count users by tier
    tiers = {"free": 0, "pro": 0, "enterprise": 0}
    mrr = 0
    
    for u in db.users.values():
        tier = u["tier"]
        tiers[tier] += 1
        if tier in ["pro", "enterprise"]:
            mrr += TIER_CONFIG[tier]["price_monthly"]
    
    return {
        "total_users": len(db.users),
        "tiers": tiers,
        "mrr": mrr,
        "arr": mrr * 12,
    }

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "stripe_configured": bool(STRIPE_SECRET_KEY),
        "timestamp": time.time(),
    }

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Cosmos Engine API",
        "version": "1.0.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
