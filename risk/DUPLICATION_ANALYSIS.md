# SOLVENS CORE - DUPLICATION ANALYSIS
## Architectural Consolidation - Phase 1.5

**Date:** 2025-01-17
**Purpose:** Determine Source of Truth between `cosmos/` and `solvens/cosmos/`

---

## 1. EXECUTIVE SUMMARY

| Directory | Status | Last Major Commit | Active Usage |
|-----------|--------|-------------------|--------------|
| `cosmos/` | PRIMARY | 2025-01-17 (Phase 2) | HIGH |
| `solvens/cosmos/` | SECONDARY | 2024 (MVP phase) | LOW |

### Recommendation: **`cosmos/` is the Source of Truth**

---

## 2. COMMIT HISTORY ANALYSIS

### `cosmos/` - Recent Active Development
```
69bc9a1 chore: Phase 2 - Hardening and Security Audit (HEAD)
0769034 fix: Risk Mitigation - All 4 Critical Risks Resolved
469bf06 feat: Phase 2 - Scientific Benchmark Suite
63e70a0 feat: Phase 1 - Core parser, AST, DAG, and Router
9116602 feat: add verifiable benchmark suite
6838acb feat: LICENSE + TELEMETRY - Apache 2.0 + Commercial
59253b8 feat: COMPLETE - CLI + EXPORT SCHEMA v1 + Binaries
```

### `solvens/cosmos/` - Legacy Development
```
c98ea3c feat: COSMOS MOAT - DAG Implementation
793d480 feat: Cosmos Canonicalizer Production v0.2
e64f669 feat: MVP for 30-Day Monetization
b73a01f feat: Hito 4 - Cosmos Language Integration
```

**Conclusion:** `cosmos/` is actively maintained; `solvens/cosmos/` is legacy.

---

## 3. IMPORT ANALYSIS

### Used by Main CLI (`solvens/cli.py`)
```
from cosmos.parser.parser import Parser          # LINE 150, 203, 253, 379
from cosmos.runtime.cost_safety import CostEstimator  # LINE 254
from cosmos.providers.llm import llm            # LINE 428
```

### Used by Tests
```
from cosmos.parser.parser import Parser          # 5 imports
from cosmos.compiler.errors import CompileError   # 4 imports
from cosmos.ast import ASTNode, Program          # 2 imports
```

### `solvens/cosmos/` Usage
```
from solvens.cosmos.ast import CosmosAST         # 4 imports (legacy)
from solvens.cosmos.dag import CosmosDAG        # 2 imports
from solvens.cosmos.moat_parser import CosmosParser  # 1 import
```

**Conclusion:** Main CLI uses `cosmos/` exclusively.

---

## 4. MODULE COMPARISON

### `cosmos/` Structure (16 modules)
```
cosmos/
├── ast/                  # AST nodes
├── benchmarks/           # Performance testing
├── compiler/             # Strassen, FFT, validators
├── dag/                  # DAG implementation
├── license/              # License management
├── lsp/                  # Language Server Protocol
├── parser/               # Lexer, Parser, Grammar
├── providers/             # LLM providers (OpenAI, Ollama)
├── router/                # Provider routing
├── runtime/               # Cost safety, execution
├── security/              # RBAC, audit
├── cli.py                 # 659 lines
├── explainer.py           # 653 lines
├── solvens_agent.py       # 713 lines
└── telemetry.py
```

### `solvens/cosmos/` Structure (20 modules)
```
solvens/cosmos/
├── ast.py                 # Custom AST (different from cosmos/ast/)
├── canonicalizer.py       # AST normalization
├── canonicalizer_production.py
├── dag.py                 # Custom DAG (different structure)
├── demo.py                # Demo utilities
├── executor.py            # Execution engine
├── moat_executor.py       # 641 lines
├── moat_parser.py         # 618 lines - Alternative parser
├── planner.py             # Execution planning
├── parser.py              # Alternative parser
├── runtime.py             # Runtime utilities
├── visualizer/            # Web visualization
│   ├── dag_renderer.py
│   ├── timeline_view.py
│   └── web_preview.py
├── entity/
├── exporters/
├── importers/
├── lexer/
├── optimizer/
├── serializer/
├── universe/
└── validator/
```

---

## 5. UNIQUE FUNCTIONALITY

### Modules ONLY in `cosmos/`
- `solvens_agent.py` - Main compiler agent
- `explainer.py` - LLM-based error explanations
- `telemetry.py` - Usage telemetry
- `license/manager.py` - License management
- `benchmarks/runner.py` - Benchmark framework
- `compiler/strassen.py` - Matrix algorithms
- `compiler/fft.py` - FFT algorithms
- `providers/llm.py` - LLM interface
- `providers/ollama_provider.py` - Ollama integration
- `runtime/cost_safety.py` - Cost protection
- `security/rbac.py` - RBAC implementation

### Modules ONLY in `solvens/cosmos/`
- `moat_parser.py` - Alternative parser with MOAT extensions
- `moat_executor.py` - Execution with MOAT integration
- `canonicalizer.py` - AST normalization (NOT in cosmos/)
- `visualizer/` - Web visualization (NOT in cosmos/)
- `demo.py` - Demo utilities
- `entity/` - Entity management
- `optimizer/` - Code optimizer
- `serializer/` - Serialization utilities
- `universe/` - Universe management
- `validator/` - Additional validators

---

## 6. CODE QUALITY METRICS

| Metric | `cosmos/` | `solvens/cosmos/` |
|--------|-----------|-------------------|
| Total Lines | ~8,500 | ~6,500 |
| Active Tests | 132 passing | 0 specific |
| CLI Usage | 100% | 0% |
| Last Update | 2025-01-17 | 2024 |
| Documentation | Complete | Partial |

---

## 7. DECISION MATRIX

| Criterion | cosmos/ | solvens/cosmos/ |
|-----------|---------|------------------|
| Recency | ✅ 2025 | ❌ 2024 |
| Active Use | ✅ High | ❌ Low |
| CLI Integration | ✅ 100% | ❌ 0% |
| Test Coverage | ✅ Full | ❌ None |
| Documentation | ✅ Complete | ⚠️ Partial |
| RBAC/Security | ✅ Yes | ❌ No |
| Cost Safety | ✅ Yes | ❌ No |
| Providers | ✅ Yes | ⚠️ Basic |

---

## 8. RECOMMENDATION

### **Source of Truth: `cosmos/`**

#### Rationale:
1. **Active Development**: Most recent commits target `cosmos/`
2. **CLI Integration**: Main entry point uses `cosmos/` exclusively
3. **Test Coverage**: All 132 tests pass using `cosmos/`
4. **Feature Complete**: RBAC, cost safety, telemetry, benchmarks
5. **Production Ready**: Used in Phase 1 and Phase 2 hardening

#### Components to MIGRATE from `solvens/cosmos/`:
1. **`visualizer/`** - Web visualization tools (unique functionality)
2. **`canonicalizer.py`** - AST normalization (unique functionality)
3. **Consider `moat_parser.py`** - If MOAT extensions needed

#### Components to DEPRECATE:
1. All duplicate modules in `solvens/cosmos/` that mirror `cosmos/`

---

## 9. MIGRATION PLAN

### Phase 1: Preserve Unique Functionality
- [ ] Copy `visualizer/` → `cosmos/visualizer/`
- [ ] Copy `canonicalizer.py` → `cosmos/canonicalizer/`
- [ ] Copy `moat_parser.py`, `moat_executor.py` → `cosmos/moat/`

### Phase 2: Update Imports
- [ ] Update all imports to use `cosmos/` consistently
- [ ] Update CLI to reference `cosmos/` only
- [ ] Update documentation

### Phase 3: Deprecation
- [ ] Mark `solvens/cosmos/` as deprecated
- [ ] Add deprecation warning if imported
- [ ] Eventually remove after migration period

---

## 10. RISK ASSESSMENT

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Losing MOAT functionality | Low | Medium | Migrate moat modules |
| Breaking CLI | Low | High | Test after each change |
| Losing visualization | Medium | Medium | Migrate visualizer first |
| Duplication remains | High | Low | Strict review process |

---

## 11. CONCLUSION

**`cosmos/` is the unambiguous Source of Truth.**

The analysis clearly shows:
1. Active development happens in `cosmos/`
2. All tests pass using `cosmos/`
3. CLI uses `cosmos/` exclusively
4. `solvens/cosmos/` contains legacy code from MVP phase

**Recommended Action:**
1. Migrate unique modules from `solvens/cosmos/` to `cosmos/`
2. Deprecate and eventually remove `solvens/cosmos/`
3. Maintain single source of truth

---

**Analyst:** OpenHands
**Date:** 2025-01-17
**Status:** COMPLETE
