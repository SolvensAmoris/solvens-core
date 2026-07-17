# SOLVENS Enterprise

Self-hosted, on-premises deployment for regulated industries.

## Quick Start

```bash
# Single command deployment
docker compose up -d

# Kubernetes with Helm
helm install solvens ./k8s/helm-chart \
  --set license.key=YOUR_LICENSE_KEY
```

## Features

- 🔐 **Zero-Internet Mode** - Runs completely offline
- 🏦 **SOC2/HIPAA/GDPR Ready** - Compliance documentation included
- 📊 **FinOps** - Per-team budgets and cost tracking
- 🔒 **RBAC** - Role-based access control
- 📝 **Immutable Audit Logs** - SHA256 chain integrity
- 🛡️ **PII Redaction** - Automatic before external API calls
- 📈 **Prometheus Metrics** - Full observability
- ☸️ **Kubernetes Ready** - Helm chart with HPA

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SOLVENS Enterprise                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │  API     │    │Dashboard │    │ Ollama   │              │
│  │  Server  │    │  (Next)  │    │  (LLM)   │              │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘              │
│       │               │               │                      │
│  ┌────┴───────────────┴───────────────┴────┐              │
│  │           Redis (Cache/Queue)            │              │
│  └─────────────────┬───────────────────────┘              │
│                    │                                        │
│  ┌────────────────┴────────────────┐                      │
│  │       PostgreSQL                 │                      │
│  │  (Metadata + Immutable Audit)   │                      │
│  └─────────────────────────────────┘                      │
│                                                              │
│  ┌────────────────────────────────┐                        │
│  │  MinIO (S3-compatible storage) │                        │
│  └────────────────────────────────┘                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Requirements

### Docker Compose
- Docker 24.0+
- 16GB RAM minimum
- 100GB storage

### Kubernetes
- K8s 1.27+
- 32GB RAM per node
- Persistent volumes (100GB+)

## Security

### Network Isolation
- All traffic internal
- No external API calls required
- Optional: configure egress firewall

### Data Encryption
- AES-256-GCM at rest
- TLS 1.3 in transit
- Customer-managed keys via Vault

### Compliance
- SOC2 Type II (Q1 2025)
- HIPAA BAA available
- GDPR DPA available

## Documentation

- [Compliance](security/COMPLIANCE.md)
- [RBAC](security/rbac.py)
- [Audit Logging](security/audit.py)
- [PII Redaction](security/pii_redaction.py)
- [Metrics](observability/metrics.py)

## Support

- Enterprise SLA: 99.9%
- Dedicated Slack Connect
- Phone support available

**Contact:** enterprise@solvens.amolis
