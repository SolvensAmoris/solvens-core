# 🚀 DEPLOYMENT GUIDE
## Cosmos Engine - Production Ready

---

# 1. QUICK START

## Local Development

```bash
cd /workspace/project/solvens-core

# Install dependencies
pip install -r api/requirements.txt

# Run API
uvicorn api.main:app --reload --port 8000

# Open browser
open http://localhost:8000
```

## Test API

```bash
# Health check
curl http://localhost:8000/health

# Register user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'
```

---

# 2. STRIPE SETUP

## Create Stripe Account

1. Go to [stripe.com](https://stripe.com)
2. Create account
3. Get API keys from Dashboard

## Create Products & Prices

```bash
# Using Stripe CLI
stripe products create --name="Cosmos Pro" --description="Pro tier access"

# Create price (monthly)
stripe prices create \
  --product="prod_xxx" \
  --unit-amount=4900 \
  --currency=usd \
  --recurring[interval]=month

# Create price (yearly)
stripe prices create \
  --product="prod_xxx" \
  --unit-amount=47000 \
  --currency=usd \
  --recurring[interval]=year
```

## Environment Variables

```bash
# .env file
STRIPE_SECRET_KEY=sk_live_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx
STRIPE_PRO_PRICE_ID=price_xxxxx
STRIPE_ENTERPRISE_PRICE_ID=price_xxxxx
BASE_URL=https://yourdomain.com
JWT_SECRET=your-super-secret-key-change-in-production
```

## Local Webhook Testing

```bash
# Install Stripe CLI
brew install stripe/stripe-cli/stripe

# Login
stripe login

# Forward webhooks to localhost
stripe listen --forward-to localhost:8000/api/webhooks/stripe

# Copy the webhook signing secret
# Set STRIPE_WEBHOOK_SECRET=whsec_xxx
```

---

# 3. VERCEL DEPLOYMENT

## vercel.json

```json
{
  "version": 2,
  "builds": [
    { "src": "api/main.py", "use": "@vercel/python" }
  ],
  "routes": [
    { "src": "/api/(.*)", "dest": "api/main.py" },
    { "src": "/(.*)", "dest": "/api/landing.html" }
  ],
  "env": {
    "STRIPE_SECRET_KEY": "@stripe_secret_key",
    "STRIPE_WEBHOOK_SECRET": "@stripe_webhook_secret",
    "STRIPE_PRO_PRICE_ID": "@stripe_pro_price_id",
    "STRIPE_ENTERPRISE_PRICE_ID": "@stripe_enterprise_price_id",
    "BASE_URL": "@base_url",
    "JWT_SECRET": "@jwt_secret"
  }
}
```

## Deploy

```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy
vercel --prod
```

## Configure Stripe Webhooks

1. Go to Stripe Dashboard → Webhooks
2. Add endpoint: `https://yourdomain.com/api/webhooks/stripe`
3. Select events:
   - `checkout.session.completed`
   - `customer.subscription.deleted`
   - `invoice.payment_failed`
4. Copy signing secret to Vercel env vars

---

# 4. POST-DEPLOYMENT CHECKLIST

## Verification Steps

```bash
# 1. Health check
curl https://yourdomain.com/health

# 2. Register new user
curl -X POST https://yourdomain.com/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"newuser@example.com","password":"test123"}'

# 3. Get auth token from response
# Use token in subsequent requests

# 4. Test checkout (should redirect to Stripe)
curl -X POST https://yourdomain.com/api/checkout \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tier":"pro"}'

# 5. Test webhook (simulate with Stripe CLI)
stripe trigger checkout.session.completed
```

## Security Checklist

- [ ] STRIPE_SECRET_KEY is set (not in code)
- [ ] STRIPE_WEBHOOK_SECRET is set
- [ ] JWT_SECRET is changed from default
- [ ] BASE_URL is set correctly
- [ ] HTTPS enabled
- [ ] Rate limiting enabled on API

---

# 5. MONITORING

## Admin Dashboard

```bash
# Get all users
curl https://yourdomain.com/api/admin/users \
  -H "Authorization: Bearer ADMIN_TOKEN"

# Get revenue stats
curl https://yourdomain.com/api/admin/revenue \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

## Expected Response

```json
{
  "total_users": 42,
  "tiers": { "free": 30, "pro": 10, "enterprise": 2 },
  "mrr": 2990,
  "arr": 35880
}
```

---

# 6. COMMON ISSUES

## Webhook Not Working

1. Check webhook endpoint is accessible
2. Verify webhook secret matches
3. Check Stripe Dashboard for webhook logs
4. Test with Stripe CLI: `stripe listen --forward-to localhost:8000/api/webhooks/stripe`

## Users Not Upgrading

1. Check checkout session is created
2. Verify success_url redirect works
3. Check webhook is receiving events
4. Verify tier is being set in database

## Rate Limiting Not Working

1. Check STRIPE_RATE_LIMIT is set
2. Verify billing middleware is loaded
3. Test with multiple concurrent requests

---

# 7. PRODUCTION CONSIDERATIONS

## Database

For MVP: In-memory database is fine.
For production: Replace with PostgreSQL.

```python
# Example with SQLAlchemy
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
Session = sessionmaker(bind=engine)
Base = declarative_base()
```

## Authentication

For MVP: Simple JWT tokens.
For production: Consider adding refresh tokens, password reset, 2FA.

## Error Handling

All API errors should:
1. Log to monitoring (Sentry, Datadog)
2. Return appropriate HTTP status
3. Include error ID for debugging

---

# 8. SUPPORT

- Email: support@cosmosengine.ai
- GitHub Issues: github.com/SolvensAmoris/solvens-core/issues

---

*Last updated: 2025-01-18*
