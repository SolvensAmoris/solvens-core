# SmartRouter Analysis

**Fecha:** 2025-01-17  
**Analista:** OpenHands  
**Versión:** 0.5.0-rc1  

---

## Resumen Ejecutivo

SmartRouter es un sistema de enrutamiento inteligente que selecciona el mejor provider de IA basándose en:
- Tipo de tarea (code, research, vision, etc.)
- Costo
- Latencia
- Disponibilidad

**Ubicación actual:** `solvens/router/smart_router.py`  
**Ubicación objetivo:** `cosmos/router/smart_router.py`

---

## Responsabilidades

### Core Responsibilities

| Responsabilidad | Descripción | Estado |
|----------------|-------------|--------|
| Enrutamiento inteligente | Selecciona provider óptimo | ✅ Implementado |
| Detección automática | Detecta tipo de task por keywords | ✅ Implementado |
| Scoring de providers | Calcula score basado en costo/latencia | ✅ Implementado |
| Fallback | Provee cadena de fallback | ✅ Implementado |
| Stats/Logging | Registra uso y costos | ✅ Implementado |
| Auto-detección | Detecta keywords en prompts | ✅ Implementado |

### Providers Soportados

| Provider | Tipo | Costo Input | Costo Output | Latencia |
|----------|------|-------------|--------------|----------|
| Grok | Cloud | $2/1M | $10/1M | ~2000ms |
| Ollama | Local | $0 | $0 | ~500ms |
| OpenAI | Cloud | Variable | Variable | ~500ms |
| Anthropic | Cloud | Variable | Variable | ~500ms |
| Google | Cloud | Variable | Variable | ~500ms |
| DeepSeek | Cloud | Variable | Variable | ~500ms |

### Task Types

```
CODE, RESEARCH, VISION, REASONING, FAST, CREATIVE, LEGAL, ANALYSIS
```

---

## Dependencias Detectadas

### Archivos que importan SmartRouter

| Archivo | Importa | Uso |
|---------|---------|-----|
| `cosmos/moat/moat_executor.py` | SmartRouter, TaskType | Enrutamiento MOAT |
| `solvens/cli/launch.py` | SmartRouter, TaskType, ProviderType, get_router | CLI launch |
| `solvens/cli/cosmos.py` | get_router | CLI cosmos |

### Dependencias Internas

```
SmartRouter
├── Provider (ABC)
│   ├── GrokProvider
│   └── OllamaProvider
├── ProviderConfig (dataclass)
├── RoutingResult (dataclass)
├── ProviderType (Enum)
└── TaskType (Enum)
```

### Dependencias Externas

| Módulo | Uso |
|--------|-----|
| asyncio | Llamadas async |
| logging | Logging |
| os | Variables de entorno (GROK_API_KEY) |
| dataclasses | ProviderConfig, RoutingResult |
| enum | ProviderType, TaskType |

---

## API Pública

### Clases Principales

```python
# Enums
class ProviderType(Enum):
    GROK, OLLAMA, OPENAI, ANTHROPIC, GOOGLE, DEEPSEEK

class TaskType(Enum):
    CODE, RESEARCH, VISION, REASONING, FAST, CREATIVE, LEGAL, ANALYSIS

# Data Classes
@dataclass
class ProviderConfig:
    name: str
    provider_type: ProviderType
    api_key: Optional[str]
    base_url: Optional[str]
    model: str
    cost_input: float
    cost_output: float
    latency_ms: float
    max_tokens: int
    enabled: bool
    priority: int

@dataclass
class RoutingResult:
    provider: ProviderType
    model: str
    estimated_cost: float
    estimated_latency_ms: float
    reason: str

# Main Class
class SmartRouter:
    def register_provider(provider: Provider)
    def register_task_keywords(keywords: Dict[str, str])
    def detect_task_type(prompt: str) -> TaskType
    def score_provider(provider, task_type, estimated_tokens) -> float
    async def route(prompt, task_type, preferred_provider, estimated_tokens) -> RoutingResult
    async def execute(prompt, messages, **kwargs) -> Dict
    def get_stats() -> Dict

# Global
def get_router() -> SmartRouter
```

---

## Comparación: cosmos/router vs solvens/router

### cosmos/router (Básico)

```python
class ProviderRouter:
    def register_provider(provider: Provider)
    def route(request: RouteRequest) -> RouteResult
    def get_cheapest_provider() -> Provider
    def get_fastest_provider() -> Provider
```

**Diferencias:**
- No tiene TaskType
- No tiene scoring avanzado
- No tiene auto-detección
- No tiene providers reales (Grok, Ollama)

### solvens/router/SmartRouter (Completo)

```python
class SmartRouter:
    def register_provider(provider: Provider)
    def register_task_keywords(keywords)
    def detect_task_type(prompt) -> TaskType
    def score_provider(provider, task_type, tokens) -> float
    async def route(prompt, task_type, preferred_provider) -> RoutingResult
    async def execute(prompt, messages) -> Dict
    def get_stats() -> Dict
```

**Ventajas:**
- Scoring inteligente
- Auto-detección de tipo de task
- Stats detallados
- Providers funcionales

---

## Riesgos de Migración

| Riesgo | Nivel | Mitigación |
|--------|-------|------------|
| Breaking API | Alto | Mantener backwards compat |
| Tests fallan | Medio | No cambiar signature |
| Dependencias circulares | Bajo | Verificar imports |
| CLI rota | Alto | Actualizar CLI también |

---

## Plan de Migración Recomendado

### Opción 1: Copiar y Adaptar (RECOMENDADA)

1. Copiar `solvens/router/smart_router.py` → `cosmos/router/smart_router.py`
2. Actualizar imports en `cosmos/moat/moat_executor.py`
3. Mantener `solvens/router/smart_router.py` con deprecation warning
4. Actualizar CLI
5. Tests deben pasar sin cambios

### Opción 2: Merge con ProviderRouter existente

1. Integrar SmartRouter con ProviderRouter en `cosmos/router/`
2. Más complejo, mayor riesgo

---

## Recomendación

**Usar Opción 1: Copiar y Adaptar**

Riesgo: BAJO  
Esfuerzo: ~2 horas  
Beneficio: Arquitectura limpia, código en cosmos/

---

## Estado de Decisión

**Pendiente:** Esperar confirmación de Luis para proceder.
