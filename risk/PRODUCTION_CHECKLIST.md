# SOLVENS Production Go/No-Go Checklist

**IF ANY ITEM HAS ❌ = NO DEPLOY**

---

## 🔴 CRITICAL BLOCKERS (Must be ✅ before any production deployment)

### Cost Safety
- [ ] ✅ `max_cost_usd` circuit breaker implemented in scheduler
- [ ] ✅ Per-team budget limits enforced
- [ ] ✅ Rate limiting: 10 runs/min per IP
- [ ] ✅ Loop detection: max DAG depth 20

### Security
- [ ] ✅ RBAC: viewer role cannot execute workflows
- [ ] ✅ PII redaction: SSN, credit cards, API keys redacted
- [ ] ✅ Immutable audit logs with SHA256 chain
- [ ] ✅ No arbitrary HTTP egress from agents

### Reliability
- [ ] ✅ Health check endpoint `/health`
- [ ] ✅ Graceful shutdown with run recovery
- [ ] ✅ Retry with exponential backoff
- [ ] ✅ Provider failover <500ms

### Compliance
- [ ] ✅ SOC2 controls documented
- [ ] ✅ GDPR data subject endpoints
- [ ] ✅ HIPAA BAA available (if healthcare)
- [ ] ✅ Audit log export to SIEM

---

## 🟡 SECURITY HARDENING (Must be ✅ before enterprise deployment)

### Authentication
- [ ] ✅ JWT validation with expiry
- [ ] ✅ API key scopes enforced
- [ ] ✅ SSO integration: Okta/Azure AD/Google

### Authorization
- [ ] ✅ Role hierarchy: OWNER > ADMIN > EDITOR > DEVELOPER > VIEWER
- [ ] ✅ Per-workflow ACLs
- [ ] ✅ Workflow-level permissions

### Network
- [ ] ✅ TLS 1.3 for all connections
- [ ] ✅ Kubernetes NetworkPolicies
- [ ] ✅ Egress firewall rules
- [ ] ✅ No default credentials

### Secrets
- [ ] ✅ API keys in vault/secrets manager
- [ ] ✅ No secrets in code or git
- [ ] ✅ Secrets rotation policy

---

## 🟢 OPERATIONAL EXCELLENCE (Should be ✅ before GA)

### Observability
- [ ] ✅ Prometheus metrics exposed
- [ ] ✅ Distributed tracing (OpenTelemetry)
- [ ] ✅ Structured logging (JSON)
- [ ] ✅ Alerting: PagerDuty/Slack

### Performance
- [ ] ✅ Latency P99 <2s at 1K RPS
- [ ] ✅ Memory <1.5GB peak
- [ ] ✅ Cost <$0.004/run

### Scalability
- [ ] ✅ Horizontal pod autoscaling
- [ ] ✅ Database connection pooling
- [ ] ✅ Redis cache for hot paths
- [ ] ✅ CDN for static assets

### Disaster Recovery
- [ ] ✅ Backup strategy documented
- [ ] ✅ RTO <15 minutes
- [ ] ✅ RPO <5 minutes
- [ ] ✅ Chaos engineering tests

---

## 🔵 LEGAL & COMPLIANCE (Must be ✅ before EU/Healthcare/Finance)

### Legal
- [ ] ✅ Terms of Service drafted
- [ ] ✅ Privacy Policy drafted
- [ ] ✅ Cookie consent (if applicable)
- [ ] ✅ DPA available for enterprise

### EU AI Act (if selling in EU)
- [ ] ✅ Registered with EU AI Office
- [ ] ✅ Human-in-loop mode
- [ ] ✅ Conformity assessment
- [ ] ✅ DPIA completed

### SOC2 (if enterprise target)
- [ ] ✅ 87 controls implemented
- [ ] ✅ Evidence collection automated
- [ ] ✅ Third-party audit scheduled
- [ ] ✅ Access reviews quarterly

---

## 🟣 SUPPLY CHAIN (Must be ✅ before any pip/npm publish)

### Dependencies
- [ ] ✅ Minimal dependencies (no langchain)
- [ ] ✅ SBOM generated per release
- [ ] ✅ SBOM signed with GPG
- [ ] ✅ Reproducible builds

### Code
- [ ] ✅ No hardcoded credentials
- [ ] ✅ Static analysis (bandit, semgrep)
- [ ] ✅ Dependency scan (safety, npm audit)
- [ ] ✅ No vulnerable dependencies

### Distribution
- [ ] ✅ PyPI two-factor auth
- [ ] ✅ npm organization with 2FA
- [ ] ✅ GitHub admin protected
- [ ] ✅ Signed commits required

---

## 📊 TEST REQUIREMENTS

### Unit Tests
- [ ] ✅ >80% code coverage
- [ ] ✅ All PRs require tests
- [ ] ✅ Flaky test <1%

### Integration Tests
- [ ] ✅ Provider APIs mocked
- [ ] ✅ Database migrations tested
- [ ] ✅ Auth flow tested
- [ ] ✅ WebSocket reconnection tested

### E2E Tests
- [ ] ✅ Happy path works
- [ ] ✅ Error handling works
- [ ] ✅ Timeout handling works
- [ ] ✅ Rollback works

### Chaos Tests
- [ ] ✅ Kill 30% pods → 99.9% success
- [ ] ✅ Network partition → graceful degradation
- [ ] ✅ Provider outage → failover works
- [ ] ✅ OOM → container restart

---

## 🚀 DEPLOYMENT READINESS

### Infrastructure
- [ ] ✅ Production environment configured
- [ ] ✅ Staging mirrors production
- [ ] ✅ Blue/green deployment ready
- [ ] ✅ Rollback procedure documented

### Monitoring
- [ ] ✅ Dashboard: SLOs visible
- [ ] ✅ Alert: P99 latency >2s
- [ ] ✅ Alert: Error rate >0.1%
- [ ] ✅ Alert: Cost >$X/hour

### Runbooks
- [ ] ✅ On-call runbook
- [ ] ✅ Escalation policy
- [ ] ✅ Post-mortem template
- [ ] ✅ Customer communication template

---

## 📋 SIGN-OFF

| Role | Name | Date | Status |
|------|------|------|--------|
| Engineering Lead | | | ❌ |
| Security Lead | | | ❌ |
| Product Manager | | | ❌ |
| Legal | | | ❌ |
| Customer Success | | | ❌ |

---

## ❌ BLOCKER EXAMPLES

### Example 1: Missing Circuit Breaker
```
❌ COST_EXPLOSION: No circuit breaker
Fix: Implement max_cost_usd in scheduler.py
Status: MUST FIX before deploy
```

### Example 2: No Rate Limiting
```
❌ RATE_LIMIT: API accepts unlimited requests
Fix: Implement 10 req/min per IP
Status: MUST FIX before deploy
```

### Example 3: Viewer Can Execute
```
❌ RBAC_BYPASS: viewer role can run workflows
Fix: Add permission check in rbac.py
Status: MUST FIX before enterprise deploy
```

---

## ✅ COMPLETION EXAMPLE

```
All critical blockers: ✅
All security hardening: ✅
All operational excellence: ✅
Legal review: ✅
Sign-off: ✅

🚀 READY FOR PRODUCTION
```

---

*Document Version: 1.0*  
*Last Updated: 2025-01-17*  
*Owner: Engineering*
