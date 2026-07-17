# EXPORT SCHEMA v1.0 - For External AI

## Overview

Cosmos `export-audit` outputs a JSON/CSV schema designed for external AI consumption. Use this to feed Claude/GPT for automated PR fixes.

## Usage

```bash
# Export last 100 compilations
cosmos export-audit --format=json --last=100 > audit.json

# Filter by error code
cosmos export-audit --error-code=E401 --format=json > e401_audits.json

# CSV export
cosmos export-audit --format=csv --output=audit.csv
```

## JSON Schema

```json
{
  "version": "1.0",
  "description": "Cosmos Audit Export for External AI",
  "exported_at": "2026-07-17T14:30:00Z",
  "hostname": "laptop.local",
  "total_records": 100,
  "exports": [
    {
      "timestamp": "2026-07-17T14:25:00Z",
      "file_hash": "a3f2c1d4e5f6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1",
      "file_path": "workflows/production.cosmos",
      "status": "REJECTED",
      "error_code": "E401",
      "rule_violated": "TEMPORAL",
      "context_kg": ["planet:Earth", "light:Sun->Earth", "galaxy:Orbit"],
      "fix_suggestion": "Update expired_on to 2027-12-31 or remove conflicting lights",
      "cache_hit": false,
      "compile_time_ms": 8.5,
      "metadata": {}
    }
  ]
}
```

## Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Schema version (always "1.0") |
| `exported_at` | ISO8601 | Timestamp of export |
| `total_records` | int | Number of records exported |
| `exports` | array | Array of compilation records |
| `timestamp` | ISO8601 | When the compilation occurred |
| `file_hash` | string | SHA256 hash of source file |
| `file_path` | string | Path to the compiled file |
| `status` | string | APPROVED, REJECTED, or ERROR |
| `error_code` | string? | E401, E402, E403, etc. (null if APPROVED) |
| `rule_violated` | string? | TEMPORAL, TOPOLOGY, FLOW, CYCLE (null if APPROVED) |
| `context_kg` | array | Related nodes from HybridKnowledgeGraph |
| `fix_suggestion` | string? | LLM-generated fix recommendation |
| `cache_hit` | bool | Whether result was served from cache |
| `compile_time_ms` | float | Compilation time in milliseconds |

## Error Code Mappings

| Error Code | Rule Violated | Description |
|------------|---------------|-------------|
| E401 | TEMPORAL | TemporalConstraintViolation (fail-fast) |
| E402 | CYCLE | TemporalCycleDetected |
| E403 | TEMPORAL | InvalidTemporalOrder |
| E404 | TEMPORAL | DurationExceeded |
| E405 | TEMPORAL | TemporalInconsistency |
| E200 | TOPOLOGY | DuplicateNode |
| E201 | TOPOLOGY | UndefinedReference |
| E202 | TOPOLOGY | CircularDependency |
| E100 | SYNTAX | SyntaxError |
| E101 | SYNTAX | InvalidUniverse |
| E102 | SYNTAX | InvalidNodeType |

## Usage with Claude/GPT

### Example: Automated PR Fix

```python
import json
import anthropic

# Get audits with errors
audits = json.load(open("e401_audits.json"))

client = anthropic.Anthropic()

for audit in audits["exports"]:
    if audit["error_code"] == "E401":
        prompt = f"""
Fix this Cosmos file:

File: {audit['file_path']}
Error: {audit['error_code']} - {audit['fix_suggestion']}
Context: {audit['context_kg']}

Original file content (read from disk)...

Please provide the corrected Cosmos code.
"""
        response = client.messages.create(
            model="claude-3-5-sonnet",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Create PR with fix
        create_pr(f"fix: {audit['file_path']}", response.content)
```

### Example: Batch Analysis

```python
import json
from collections import Counter

audits = json.load(open("audit.json"))

# Count errors by type
error_counts = Counter(a["error_code"] for a in audits["exports"] if a["error_code"])

# Most common violations
for error, count in error_counts.most_common(10):
    print(f"{error}: {count}")

# Average compile time
compile_times = [a["compile_time_ms"] for a in audits["exports"]]
print(f"Avg compile time: {sum(compile_times)/len(compile_times):.2f}ms")
```

## CSV Format

```csv
timestamp,file_hash,file_path,status,error_code,rule_violated,cache_hit,compile_time_ms,fix_suggestion
2026-07-17T14:25:00Z,a3f2c1d4e5f6,workflows/prod.cosmos,REJECTED,E401,TEMPORAL,false,8.5,Update expired_on...
```

## Integration Points

### GitHub Actions

```yaml
- name: Export Cosmos audits
  run: cosmos export-audit --format=json --last=1000 > cosmos_audits.json

- name: Send to Claude
  env:
    CLAUDE_API_KEY: ${{ secrets.CLAUDE_API_KEY }}
  run: python scripts/fix_audits.py cosmos_audits.json
```

### CI/CD Pipeline

```bash
# In your CI pipeline
cosmos compile --strict ./**/*.cosmos --json > results.json
cosmos export-audit --format=json --last=1000 > audit.json

# Attach to PR
gh pr comment $PR --body-file audit_summary.md
```

---

*Author: Luis Alberto Burciaga Miker*  
*Version: 0.4.5-rc1*
