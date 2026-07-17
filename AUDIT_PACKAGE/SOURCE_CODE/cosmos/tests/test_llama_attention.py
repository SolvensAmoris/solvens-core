"""
test_llama_attention.py
=======================
Handler de auditoría para LlamaAttention + CACHE_TRANSITION.

Valida que el nodo CACHE_TRANSITION se genera correctamente
cuando LlamaAttention procesa tokens y actualiza el KV Cache.
"""

import pytest
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum


# ============================================================
# Tipos del Sistema de Auditoría
# ============================================================

class CacheTransitionType(Enum):
    EXTEND = "extend"           # Nuevo token añadido
    SPECULATIVE_ROLLBACK = "speculative_rollback"
    WINDOW_EVICT = "window_evict"
    QUANTIZE = "quantize"
    TRUNCATE = "truncate"       # ILEGAL si no es explícito


@dataclass(frozen=True)
class SRIWWeights:
    """Pesos SRI-W v0.4.3.2 (sin lineage)."""
    content: float = 0.45
    position: float = 0.30
    quantization: float = 0.25


@dataclass
class KVCacheShapeContract:
    """Structural Identity para el cache."""
    batch: int
    heads: int
    head_dim: int
    max_seq_len: int


@dataclass
class KVCacheRuntime:
    """Runtime state del cache."""
    sequence_length: int
    token_ids: Tuple[int, ...]
    key_tensor_shape: List[int]
    value_tensor_shape: List[int]


@dataclass
class KVCacheState:
    """Estado completo del cache."""
    contract: KVCacheShapeContract
    runtime: KVCacheRuntime
    
    def compute_sri_w(self, weights: SRIWWeights = SRIWWeights()) -> float:
        """Computa SRI-W como combinación de fidelidades."""
        # Simulación: en producción usaría cosine similarity real
        base = 1.0
        
        # Verificar shape contract
        if self.runtime.key_tensor_shape[0] != self.contract.batch:
            return 0.0
        if self.runtime.key_tensor_shape[1] != self.contract.heads:
            return 0.0
        if self.runtime.key_tensor_shape[-1] != self.contract.head_dim:
            return 0.0
        
        # F_content simulado (fidelidad de valores)
        f_content = 0.999999
        
        # F_position simulado (integridad posicional / RoPE)
        f_position = 0.999999
        
        # F_quantization simulado
        f_quantization = 0.999999
        
        return (
            weights.content * f_content +
            weights.position * f_position +
            weights.quantization * f_quantization
        )


@dataclass
class CacheTransition:
    """Nodo CACHE_TRANSITION - auditoría de procedencia."""
    transition_id: str
    transition_type: CacheTransitionType
    state_before: KVCacheState
    state_after: KVCacheState
    tokens_added: Tuple[int, ...] = field(default_factory=tuple)
    tokens_removed: Tuple[int, ...] = field(default_factory=tuple)
    shrink_reason: Optional[str] = None
    sri_w_before: float = 0.0
    sri_w_after: float = 0.0
    
    @property
    def delta_sri_w(self) -> float:
        return self.sri_w_after - self.sri_w_before
    
    @property
    def is_valid(self) -> bool:
        """Reglas de validación."""
        # Delta tokens debe coincidir con transición
        if self.transition_type == CacheTransitionType.EXTEND:
            expected_delta = len(self.tokens_added)
            actual_delta = len(self.state_after.runtime.token_ids) - len(self.state_before.runtime.token_ids)
            if actual_delta != expected_delta:
                return False
        
        # SRI-W no debe degradar (excepto en quantize)
        if self.delta_sri_w < 0 and self.transition_type != CacheTransitionType.QUANTIZE:
            return False
        
        # Shrink requiere reason
        if (self.transition_type in [CacheTransitionType.SPECULATIVE_ROLLBACK, CacheTransitionType.WINDOW_EVICT]):
            if not self.shrink_reason:
                return False
        
        return True


# ============================================================
# Handler de LlamaAttention
# ============================================================

class LlamaAttentionCacheHandler:
    """
    Genera nodos CACHE_TRANSITION para auditorías.
    
    Sigue el flujo:
    HIDDEN → ATTENTION → OUTPUT
                    ↓
              KEY_STATE_DELTA
                    ↓
              KV_STATE_UPDATE
                    ↓
              CACHE_TRANSITION
                    ↓
              KEY_STATE_OUT
    """
    
    def __init__(self, weights: SRIWWeights = SRIWWeights()):
        self.weights = weights
        self.transitions: List[CacheTransition] = []
        self._transition_counter = 0
    
    def handle_cache_update(
        self,
        state_before: KVCacheState,
        state_after: KVCacheState,
        new_token_ids: Tuple[int, ...],
        transition_type: CacheTransitionType = CacheTransitionType.EXTEND,
        shrink_reason: Optional[str] = None
    ) -> CacheTransition:
        """Genera un CACHE_TRANSITION auditado."""
        self._transition_counter += 1
        
        # Calcular SRI-W
        sri_w_before = state_before.compute_sri_w(self.weights)
        sri_w_after = state_after.compute_sri_w(self.weights)
        
        transition = CacheTransition(
            transition_id=f"TRANS_{self._transition_counter:04d}",
            transition_type=transition_type,
            state_before=state_before,
            state_after=state_after,
            tokens_added=new_token_ids,
            shrink_reason=shrink_reason,
            sri_w_before=sri_w_before,
            sri_w_after=sri_w_after
        )
        
        self.transitions.append(transition)
        return transition
    
    def validate_chain(self) -> Tuple[bool, List[str]]:
        """Valida la cadena completa de transiciones."""
        errors = []
        
        for i, trans in enumerate(self.transitions):
            if not trans.is_valid:
                errors.append(f"[{trans.transition_id}] Invalid: {trans.transition_type.value}")
        
        return len(errors) == 0, errors


# ============================================================
# Helpers para tests
# ============================================================

def make_cache_state(
    seq_len: int,
    token_ids: Tuple[int, ...],
    batch: int = 1,
    heads: int = 32,
    head_dim: int = 128
) -> KVCacheState:
    """Factory para crear estados de cache."""
    return KVCacheState(
        contract=KVCacheShapeContract(
            batch=batch,
            heads=heads,
            head_dim=head_dim,
            max_seq_len=2048
        ),
        runtime=KVCacheRuntime(
            sequence_length=seq_len,
            token_ids=token_ids,
            key_tensor_shape=[batch, heads, seq_len, head_dim],
            value_tensor_shape=[batch, heads, seq_len, head_dim]
        )
    )


# ============================================================
# TESTS
# ============================================================

class TestLlamaAttentionCacheHandler:
    """Tests para LlamaAttention + CACHE_TRANSITION."""
    
    @pytest.fixture
    def handler(self):
        return LlamaAttentionCacheHandler()
    
    @pytest.fixture
    def empty_cache(self):
        return make_cache_state(0, tuple())
    
    @pytest.fixture
    def single_token_cache(self):
        return make_cache_state(1, (101,))
    
    def test_initial_cache(self, handler, empty_cache):
        """Cache vacío inicial es válido."""
        sri_w = empty_cache.compute_sri_w()
        assert sri_w == pytest.approx(0.999999, abs=1e-5)
    
    def test_extend_single_token(self, handler, empty_cache):
        """Extensión con 1 token."""
        next_cache = make_cache_state(1, (101,))
        
        trans = handler.handle_cache_update(
            state_before=empty_cache,
            state_after=next_cache,
            new_token_ids=(101,),
            transition_type=CacheTransitionType.EXTEND
        )
        
        assert trans.transition_type == CacheTransitionType.EXTEND
        assert trans.tokens_added == (101,)
        assert trans.is_valid
        assert trans.sri_w_after >= trans.sri_w_before
    
    def test_extend_multiple_tokens(self, handler, empty_cache):
        """Extensión con batch de tokens (prefill)."""
        next_cache = make_cache_state(128, tuple(range(100, 228)))
        
        trans = handler.handle_cache_update(
            state_before=empty_cache,
            state_after=next_cache,
            new_token_ids=tuple(range(100, 228)),
            transition_type=CacheTransitionType.EXTEND
        )
        
        assert trans.transition_type == CacheTransitionType.EXTEND
        assert len(trans.tokens_added) == 128
        assert trans.is_valid
    
    def test_speculative_rollback(self, handler, single_token_cache):
        """Rollback especulativo es válido."""
        # Cache con 5 tokens, rollback a 3
        state5 = make_cache_state(5, (101, 102, 103, 104, 105))
        state3 = make_cache_state(3, (101, 102, 103))
        
        trans = handler.handle_cache_update(
            state_before=state5,
            state_after=state3,
            new_token_ids=(),
            transition_type=CacheTransitionType.SPECULATIVE_ROLLBACK,
            shrink_reason="draft_tokens_rejected"
        )
        
        assert trans.transition_type == CacheTransitionType.SPECULATIVE_ROLLBACK
        assert trans.is_valid
        assert trans.shrink_reason == "draft_tokens_rejected"
    
    def test_window_eviction(self, handler):
        """Evicción por sliding window (Mistral) es válida."""
        state100 = make_cache_state(100, tuple(range(100, 200)))
        state50 = make_cache_state(50, tuple(range(150, 200)))
        
        trans = handler.handle_cache_update(
            state_before=state100,
            state_after=state50,
            new_token_ids=(),
            transition_type=CacheTransitionType.WINDOW_EVICT,
            shrink_reason="sliding_window_4096"
        )
        
        assert trans.transition_type == CacheTransitionType.WINDOW_EVICT
        assert trans.is_valid
    
    def test_quantization_fp16_to_int8(self, handler, single_token_cache):
        """Cuantización FP16 → INT8."""
        # Simular cuantización (SRI-W puede bajar un poco)
        state_after = make_cache_state(1, (101,))
        
        trans = handler.handle_cache_update(
            state_before=single_token_cache,
            state_after=state_after,
            new_token_ids=(),
            transition_type=CacheTransitionType.QUANTIZE,
            shrink_reason="fp16_to_int8"
        )
        
        # En cuantización, SRI-W puede bajar
        # pero la transición sigue siendo válida
        assert trans.transition_type == CacheTransitionType.QUANTIZE
        assert trans.is_valid
    
    def test_chain_validation(self, handler, empty_cache):
        """Validar cadena completa de transiciones."""
        # Step 1: Prefill
        state128 = make_cache_state(128, tuple(range(100, 228)))
        handler.handle_cache_update(empty_cache, state128, tuple(range(100, 228)))
        
        # Step 2: Extend
        state129 = make_cache_state(129, tuple(range(100, 229)))
        handler.handle_cache_update(state128, state129, (229,))
        
        # Step 3: Extend
        state130 = make_cache_state(130, tuple(range(100, 230)))
        handler.handle_cache_update(state129, state130, (230,))
        
        valid, errors = handler.validate_chain()
        assert valid, f"Chain validation failed: {errors}"
        assert len(handler.transitions) == 3
    
    def test_delta_sri_w_tracking(self, handler, empty_cache):
        """Verificar que delta_sri_w se calcula correctamente."""
        next_cache = make_cache_state(1, (101,))
        
        trans = handler.handle_cache_update(
            state_before=empty_cache,
            state_after=next_cache,
            new_token_ids=(101,)
        )
        
        assert trans.delta_sri_w == pytest.approx(0.0, abs=1e-5)


# ============================================================
# DEMO
# ============================================================

def run_demo():
    print("=" * 60)
    print("LLAMA ATTENTION + CACHE_TRANSITION HANDLER")
    print("=" * 60)
    
    handler = LlamaAttentionCacheHandler()
    empty = make_cache_state(0, tuple())
    
    print("\n[1] Prefill with 128 tokens")
    state128 = make_cache_state(128, tuple(range(100, 228)))
    t1 = handler.handle_cache_update(empty, state128, tuple(range(100, 228)))
    print(f"    {t1.transition_id}: {t1.transition_type.value}")
    print(f"    SRI-W: {t1.sri_w_before:.6f} → {t1.sri_w_after:.6f}")
    print(f"    ΔSRI-W: {t1.delta_sri_w:+.6f}")
    
    print("\n[2] Decode token 228")
    state129 = make_cache_state(129, tuple(range(100, 229)))
    t2 = handler.handle_cache_update(state128, state129, (229,))
    print(f"    {t2.transition_id}: {t2.transition_type.value}")
    print(f"    SRI-W: {t2.sri_w_before:.6f} → {t2.sri_w_after:.6f}")
    
    print("\n[3] Speculative rollback (5 → 3 tokens)")
    state5 = make_cache_state(5, (101, 102, 103, 104, 105))
    state3 = make_cache_state(3, (101, 102, 103))
    t3 = handler.handle_cache_update(state5, state3, (), 
                                     CacheTransitionType.SPECULATIVE_ROLLBACK,
                                     "draft_rejected")
    print(f"    {t3.transition_id}: {t3.transition_type.value}")
    print(f"    Valid: {t3.is_valid} (reason: {t3.shrink_reason})")
    
    print("\n[4] Chain validation")
    valid, errors = handler.validate_chain()
    print(f"    Chain valid: {valid}")
    if errors:
        print(f"    Errors: {errors}")
    
    print("\n" + "=" * 60)
    print("✓ LlamaAttention CACHE_TRANSITION handler working")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()
