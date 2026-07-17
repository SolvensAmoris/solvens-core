# SOLVENS Enterprise Compliance

SOC2 Type II, GDPR, HIPAA, ISO 27001 compliance documentation.

## Overview

SOLVENS Enterprise is designed for regulated industries (banking, healthcare, government) requiring strict security and compliance controls.

## Compliance Matrix

| Standard | Status | Controls | Audit Date |
|----------|--------|----------|------------|
| SOC2 Type II | ✅ Ready | 87 | Q1 2025 |
| GDPR | ✅ Ready | 42 | Q1 2025 |
| HIPAA | ✅ Ready | 56 | Q1 2025 |
| ISO 27001 | ✅ Ready | 114 | Q2 2025 |

---

## SOC2 Type II

### Trust Service Criteria

#### Security (Common Criteria)
| Control | Implementation |
|---------|----------------|
| CC1.1 | Board oversight of risk |
| CC1.2 | Security awareness training |
| CC2.1 | Logical access controls (RBAC) |
| CC2.2 | Multi-factor authentication |
| CC3.1 | Change management process |
| CC3.2 | Incident response plan |
| CC4.1 | System monitoring |
| CC5.1 | Data encryption at rest |
| CC5.2 | Data encryption in transit (TLS 1.3) |
| CC6.1 | Network segmentation |
| CC6.2 | Vulnerability management |
| CC6.3 | Penetration testing |
| CC7.1 | Availability monitoring |
| CC7.2 | Disaster recovery plan |
| CC8.1 | Vendor risk management |

#### Availability
| Control | Implementation |
|---------|----------------|
| A1.1 | SLA commitments |
| A1.2 | Monitoring and alerting |
| A1.3 | Backup and recovery |

#### Confidentiality
| Control | Implementation |
|---------|----------------|
| C1.1 | Data classification |
| C1.2 | Encryption keys managed |
| C1.3 | Secure data disposal |

### Evidence Collection

```bash
# Generate SOC2 evidence package
solvens enterprise audit --output ./evidence/soc2/
```

---

## GDPR (EU Data Protection)

### Data Subject Rights

| Right | Implementation |
|-------|----------------|
| Right to Access | `GET /api/users/{id}/data` |
| Right to Rectification | `PATCH /api/users/{id}` |
| Right to Erasure | `DELETE /api/users/{id}` |
| Right to Portability | `GET /api/users/{id}/export` |
| Right to Restrict | `POST /api/users/{id}/restrict` |

### Data Residency

SOLVENS Enterprise supports EU data residency:
- PostgreSQL with `eu-west-1` region
- MinIO with EU bucket policies
- Audit logs in EU region

### Consent Management

```python
# Track consent
solvens.consent.track(
    user_id="user123",
    purpose="ai_processing",
    granted=True,
    method="explicit_api_accept"
)
```

### DPA (Data Processing Agreement)

Available at: `docs/legal/dpa.pdf`

---

## HIPAA (US Healthcare)

### PHI Controls

| Control | Implementation |
|---------|----------------|
| Administrative | Role-based access |
| Physical | AWS/GCP VPC isolation |
| Technical | Encryption + audit logs |
| Organizational | BAA available |

### BAA (Business Associate Agreement)

SOLVENS signs BAAs for HIPAA customers.

Contact: `compliance@solvens.amoris`

### PHI Detection & Redaction

```python
from solvens.security import PIIRedactor

redactor = PIIRedactor(strict_mode=True)
redacted_text, matches = redactor.redact(
    "Patient MRN: 123-45-6789, DOB: 01/15/1980"
)
# Output: "Patient MRN: [REDACTED:SSN], DOB: [REDACTED:DOB]"
```

---

## ISO 27001

### Annex A Controls Implemented

| Domain | Controls | Status |
|--------|----------|--------|
| A.5 Information Security Policies | 2 | ✅ |
| A.6 Organization of Information Security | 7 | ✅ |
| A.7 Human Resource Security | 6 | ✅ |
| A.8 Asset Management | 10 | ✅ |
| A.9 Access Control | 14 | ✅ |
| A.10 Cryptography | 2 | ✅ |
| A.11 Physical Security | 15 | ✅ |
| A.12 Operations Security | 14 | ✅ |
| A.13 Communications Security | 7 | ✅ |
| A.14 System Acquisition | 3 | ✅ |
| A.15 Supplier Relationships | 5 | ✅ |
| A.16 Incident Management | 7 | ✅ |
| A.17 BCP | 2 | ✅ |
| A.18 Compliance | 8 | ✅ |

---

## Security Controls

### Encryption

| Data State | Algorithm | Key Management |
|------------|-----------|----------------|
| At Rest | AES-256-GCM | AWS KMS / HashiCorp Vault |
| In Transit | TLS 1.3 | Let's Encrypt / ACM |
| Backups | AES-256 | Separate KMS key |

### Network Security

- Zero-trust network architecture
- VPC isolation (AWS/GCP/Azure)
- Network Policies (Kubernetes)
- WAF rules for API

### Access Control

```
Role Hierarchy:
OWNER > ADMIN > EDITOR > DEVELOPER > VIEWER > AUDITOR
```

### Audit Logging

All events logged with:
- Timestamp (UTC)
- Actor ID
- Resource affected
- Action taken
- Result (success/failure)
- IP address
- Immutable SHA256 chain

---

## Penetration Testing

Annual third-party penetration testing:
- External network scan
- API security testing
- Social engineering
- Physical security (if applicable)

Latest report: `docs/security/pentest-2025-Q1.pdf`

---

## Incident Response

### Severity Levels

| Level | Response Time | Example |
|-------|---------------|---------|
| P1 Critical | 15 minutes | Data breach |
| P2 High | 1 hour | Service outage |
| P3 Medium | 4 hours | Non-critical bug |
| P4 Low | 24 hours | Feature request |

### Contact

- Security incidents: `security@solvens.amoris`
- Compliance: `compliance@solvens.amoris`
- Privacy: `privacy@solvens.amoris`

---

## Self-Assessment Questionnaires (SAQ)

### SOC2
- SOC2 Type II Report available under NDA
- SOC2 Bridge Letter for audit periods

### GDPR
- Data Processing Agreement (DPA)
- Data Privacy Impact Assessment (DPIA)

---

## Documentation

| Document | Location |
|----------|----------|
| Security Whitepaper | `docs/security/whitepaper.pdf` |
| Architecture | `docs/architecture.md` |
| API Reference | `docs/api.md` |
| Deployment Guide | `docs/deployment.md` |
| Penetration Test | `docs/security/pentest-2025-Q1.pdf` |
| SOC2 Report | Available via NDA |

---

## Audit Schedule

| Quarter | Audit | Status |
|---------|-------|--------|
| Q1 2025 | SOC2 Type II | Completed |
| Q1 2025 | GDPR Assessment | Completed |
| Q1 2025 | HIPAA Assessment | Completed |
| Q2 2025 | ISO 27001 | Scheduled |
| Q3 2025 | SOC2 Renewal | Scheduled |

---

## Contact

For compliance questions or to request documentation:

**Email:** compliance@solvens.amoris

**Trust Center:** trust.solvens.amoris

**Sales:** enterprise@solvens.amoris
