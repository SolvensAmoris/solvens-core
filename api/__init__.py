"""
Cosmos API - Production REST API

FastAPI application with:
- User authentication
- Stripe checkout + webhook
- Tier enforcement
- Usage tracking
"""

from .main import app

__all__ = ["app"]
