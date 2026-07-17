# SOLVENS Risk Audit Framework

## Purpose

This directory contains the adversarial testing and risk assessment framework for SOLVENS.
**No production deployment until all ❌ items are resolved.**

## Files

| File | Description |
|------|-------------|
| `benchmark_adversarial.py` | 7 critical tests that FAIL THE BUILD |
| `threat_model.md` | 8 threat categories with mitigations |
| `PRODUCTION_CHECKLIST.md` | Go/No-go checklist for deployment |
| `RISK_REPORT.md` | Current risk assessment summary |

## Running Tests

```bash
# Run adversarial benchmarks
cd /workspace/project/solvens-core
python -m risk.benchmark_adversarial

# Expected output:
# - 3 PASS: RBAC, basic metrics
# - 2 FAIL: Cost explosion, compatibility
# - 2 PARTIAL: Latency, vendor lock
```

## Critical Failures (Must Fix)

| Test | Issue | Fix |
|------|-------|-----|
| COST_EXPLOSION | No circuit breaker | Implement max_cost_usd |
| COMPATIBILITY | Parser incomplete | Complete parser implementation |
| VENDOR_LOCK | No auto-failover | Implement provider switching |
| MEMORY_LEAK | No process isolation | Add sandboxing |

## Threat Priority

1. **Cost Amplification** - $100K+ bill risk
2. **Prompt Injection** - Data exfiltration risk  
3. **Supply Chain** - RCE risk
4. **Regulatory** - EU AI Act compliance
5. **Vendor Lock** - 10x cost increase risk

## Production Gate

```
┌─────────────────────────────────────────┐
│           PRODUCTION GATE                 │
├─────────────────────────────────────────┤
│  ✅ All 7 benchmark tests PASS           │
│  ✅ Threat model mitigations complete    │
│  ✅ Checklist 100% complete             │
│  ✅ Legal sign-off obtained             │
└─────────────────────────────────────────┘
              │
              ▼
        🚀 DEPLOY
```

## Timeline

| Phase | Risk Work | Target |
|-------|----------|--------|
| Phase 7 | Circuit breaker, rate limiting | 1 week |
| Phase 8 | Vendor deps, SBOM, failover | 2 weeks |
| Phase 9 | Rust kernel, SOC2 audit | 4 weeks |
| Phase 10 | Production launch | Ready |

## Contact

- Security issues: security@solvens.amoris
- Risk questions: risk@solvens.amoris

---

*Last updated: 2025-01-17*
