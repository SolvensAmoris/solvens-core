# Legacy Deprecation Analysis

**Fecha:** 2025-01-17  
**Versión:** 0.5.0-rc1  
**Estado:** En Análisis

---

## Resumen Ejecutivo

Se realizó un análisis de los módulos legacy para determinar su estado de uso y planificar una deprecación controlada.

**Conclusión:** Los módulos `solvens/cosmos/` y `solvens/router/` **NO pueden ser eliminados** actualmente porque son dependencias activas del código principal.

---

## Módulos Analizados

### 1. `solvens/cosmos/` (Directorio Completo)

**Estado:** ⚠️ DEPENDENCY - No Deprecado Todavía

**Razón:** Usado activamente por:
- `cosmos/moat/moat_executor.py` - importa `solvens.cosmos.moat_parser`
- `cosmos/canonicalizer.py` - importa `solvens.cosmos.ast`

**Archivos en el directorio:**
```
solvens/cosmos/
├── __init__.py           # Exports para compatibilidad
├── ast.py                # Definiciones AST
├── canonicalizer.py      # Normalización
├── dag.py                # DAG implementation
├── demo.py               # Demo standalone
├── executor.py           # Executor legacy
├── moat_executor.py      # MOAT executor (legacy)
├── moat_parser.py        # Parser MOAT
├── parser.py             # Parser Cosmos DSL
├── planner.py            # Planner
└── runtime.py           # Runtime
```

**Imports detectados:**
| Archivo | Importa de solvens.cosmos |
|---------|--------------------------|
| cosmos/moat/moat_executor.py | ✅ Sí |
| cosmos/canonicalizer.py | ✅ Sí |
| solvens/cosmos/*.py | ✅ Auto-referencias |
| solvens/cli/run.py | ✅ Sí |
| solvens/cli/cosmos.py | ✅ Sí |
| solvens/memory/hybrid_kg.py | ✅ Sí |
| solvens/compat/langgraph_adapter.py | ✅ Sí |

**Decisión:** Mantener. Necesario para backwards compatibility.

---

### 2. `solvens/router/` (Directorio Completo)

**Estado:** ⚠️ PARTIALLY DEPRECATED - En transición

**Razón:** SmartRouter migrado a cosmos/, pero otros componentes aún usan este directorio.

**Cambios Realizados:**
- ✅ `smart_router.py` copiado a `cosmos/router/smart_router.py`
- ✅ `cosmos/moat/moat_executor.py` actualizado para usar `cosmos.router.smart_router`
- ⚠️ `solvens/router/smart_router.py` emitiendo deprecation warnings

**Dependencias restantes:**
| Archivo | Usa | Estado |
|---------|-----|--------|
| `cosmos/moat/moat_executor.py` | SmartRouter | ✅ Migrado |
| `solvens/cli/launch.py` | SmartRouter | ⚠️ Legacy |
| `solvens/cli/main.py` | CapabilityRouter | ⚠️ Legacy |
| `solvens/api/main.py` | CapabilityRouter | ⚠️ Legacy |
| `solvens/agents/orchestrator.py` | CapabilityRouter | ⚠️ Legacy |

**Plan:** Migrar CLI y API a `cosmos.router` y deprecar completamente en v0.6.0.

---

## Plan de Deprecación Controlada

### Fase 1: Documentación (Completada)
- [x] Analizar imports
- [x] Documentar dependencias
- [x] Crear este informe

### Fase 2: Migración de Dependencias (Pendiente)
- [ ] Crear `cosmos/router/smart_router.py` con misma funcionalidad
- [ ] Actualizar `cosmos/moat/moat_executor.py` para usar `cosmos.router`
- [ ] Verificar tests
- [ ] Verificar CLI funciona

### Fase 3: Deprecación Formal (Post-Fase 2)
- [ ] Agregar warnings de deprecación en solvens/cosmos/
- [ ] Agregar warnings de deprecación en solvens/router/
- [ ] Documentar reemplazo en cada archivo

### Fase 4: Eliminación (Versión Futura)
- [ ] Eliminar solvens/cosmos/ en v0.6.0
- [ ] Eliminar solvens/router/ en v0.6.0

---

## Módulos que SÍ Pueden Ser Deprecados

### `solvens/cosmos/canonicalizer_production.py`
**Estado:** ✅ ELIMINADO

Este archivo fue eliminado porque:
- No tiene imports hacia él
- No está referenciado en ningún lugar
- Es código muerto

---

## Recomendaciones

1. **NO eliminar** `solvens/cosmos/` ni `solvens/router/` todavía
2. **Migrar gradualmente** las dependencias a `cosmos/`
3. **Agregar warnings** de deprecación solo después de migración completa
4. **Mantener backwards compatibility** hasta v0.6.0

---

## Impacto de Decisión

| Opción | Impacto | Riesgo |
|--------|---------|--------|
| Eliminar ahora | Alto | Romper código activo |
| Deprecar ahora | Medio | Tests fallan |
| Migrar primero | Bajo | Trabajo adicional pero seguro |
| Mantener como está | Ninguno | Technical debt aumenta |

**Decisión adoptada:** Migrar primero, deprecar después.

---

## Estado Actual

```
solvens-core/
├── cosmos/                    # ✅ ACTIVO - SOURCE OF TRUTH
│   ├── moat/
│   │   ├── moat_parser.py    # ✅ Copia local
│   │   └── moat_executor.py  # ⚠️ Depende de solvens/cosmos/ y solvens/router/
│   └── canonicalizer.py      # ⚠️ Depende de solvens/cosmos/ast
│
├── solvens/                   # ⚠️ LEGACY - MANTENIDO POR DEPENDENCIAS
│   ├── cosmos/               # Necesario para cosmos/moat/executor
│   └── router/               # Necesario para SmartRouter
│
└── benchmarks/               # ✅ NUEVO - Sistema de benchmarks
```

---

## Acción Inmediata Requerida

Para completar la deprecación, se requiere migrar:

1. `SmartRouter` → `cosmos/router/smart_router.py`
2. `TaskType` enum → `cosmos/router/task_type.py`
3. Actualizar imports en `cosmos/moat/moat_executor.py`

**Responsable:** Equipo de desarrollo  
**Estimación:** 1-2 días  
**Bloqueante para:** Deprecación completa de solvens/router/

---

## Notas

- El código en `solvens/cosmos/` y `solvens/router/` funciona correctamente
- No hay bugs conocidos en el código legacy
- La migración es por razones de arquitectura, no por problemas técnicos
- El sistema puede operar normalmente sin migración
