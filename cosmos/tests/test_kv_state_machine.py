"""
test_kv_state_machine.py
========================
Suite de auditoría para KV Cache en Cosmos.

Casos que debe atrapar:
1. Truncate ilegal
2. Swap perdido
3. Reordenamiento
4. Duplicación de token

Casos que NO deben ser falsos positivos:
- Rollback especulativo (tokens draft rechazados)
- Sliding window (Mistral)
- Attention sinks (StreamingLLM)
- Prefill con N tokens
- Chunked prefill
"""

import pytest
from dataclasses import dataclass, field
from typing import List
from enum import Enum


class ShrinkReason(Enum):
    NONE = "none"
    SPECULATIVE_ROLLBACK = "speculative_rollback"
    WINDOW_EVICT = "window_evict"
    TRUNCATION = "truncation"  # ILEGAL


class ValidationResult:
    def __init__(self, valid: bool, message: str, shrink_reason: ShrinkReason = ShrinkReason.NONE):
        self.valid = valid
        self.message = message
        self.shrink_reason = shrink_reason
    
    def __bool__(self):
        return self.valid
    
    def __repr__(self):
        status = "VALID" if self.valid else "INVALID"
        return f"[{status}] {self.message}"


@dataclass
class KVCacheShapeContract:
    """Structural Identity - no depende del tamaño actual del cache."""
    batch: int
    heads: int
    sequence_dynamic: bool = True
    head_dim: int = 128


@dataclass 
class KVRuntimeState:
    """Runtime State - estado actual del cache."""
    actual_sequence_length: int
    tensor_storage_shape: List[int]
    token_ids: List[int] = field(default_factory=list)


@dataclass
class KVCacheState:
    """Estado completo del KV Cache."""
    contract: KVCacheShapeContract
    runtime: KVRuntimeState
    
    @property
    def sequence_length(self) -> int:
        return self.runtime.actual_sequence_length


class SRIEstimator:
    """
    ΔSRI-W = S(K_out, V_out) - S(K_in, V_in)
    
    donde S es "structural retention index" (no MI de Shannon).
    Es una métrica de forma, no de contenido.
    """
    
    @staticmethod
    def compute(state_in: KVCacheState, state_out: KVCacheState) -> float:
        """Computa ΔSRI-W (diferencia de retención estructural)."""
        s_in = SRIEstimator._structural_retention(state_in)
        s_out = SRIEstimator._structural_retention(state_out)
        return s_out - s_in
    
    @staticmethod
    def _structural_retention(state: KVCacheState) -> float:
        """Retención estructural base = 1.0 si el contrato se cumple."""
        contract = state.contract
        runtime = state.runtime
        
        if runtime.tensor_storage_shape[0] != contract.batch:
            return 0.0
        if runtime.tensor_storage_shape[1] != contract.heads:
            return 0.0
        if runtime.tensor_storage_shape[-1] != contract.head_dim:
            return 0.0
        
        retention = 1.0
        if runtime.token_ids:
            expected_length = len(runtime.token_ids)
            if expected_length != runtime.actual_sequence_length:
                retention *= 0.5
        
        return retention


@dataclass
class KVTransitionContext:
    """Contexto para validación de transición."""
    shrink_reason: ShrinkReason = ShrinkReason.NONE
    is_truncated: bool = False
    max_chunk_size: int = 1


class KVStateValidator:
    """
    Validador de transiciones KV Cache.
    """
    
    def validate(
        self, 
        state_in: KVCacheState, 
        state_out: KVCacheState,
        context: KVTransitionContext
    ) -> ValidationResult:
        delta = state_out.sequence_length - state_in.sequence_length
        
        # Regla 1: Shrinkage solo con reason válida
        if delta < 0:
            if context.shrink_reason == ShrinkReason.NONE:
                return ValidationResult(False, "KV CACHE SHRINK DETECTED - no shrink_reason")
            
            if context.shrink_reason == ShrinkReason.TRUNCATION:
                return ValidationResult(False, "ILLEGAL TRUNCATION DETECTED")
            
            return ValidationResult(True, f"VALID SHRINK ({context.shrink_reason.value})")
        
        # Regla 2: Δ debe estar en rango [0, max_chunk]
        if delta > context.max_chunk_size:
            return ValidationResult(False, f"TOKEN SPIKE: Δ={delta} > max_chunk={context.max_chunk_size}")
        
        # Regla 3: ΔSRI-W debe ser >= 0
        delta_sri = SRIEstimator.compute(state_in, state_out)
        if delta_sri < 0:
            return ValidationResult(False, f"STRUCTURAL CORRUPTION: ΔSRI-W = {delta_sri:.4f} < 0")
        
        # Regla 4: Verificar preservación de tokens
        if not self._verify_token_preservation(state_in, state_out, delta):
            return ValidationResult(False, "TOKEN REORDERING OR DUPLICATION DETECTED")
        
        return ValidationResult(True, "VALID KV EXTENSION")
    
    def _verify_token_preservation(self, state_in, state_out, delta):
        tokens_in = state_in.runtime.token_ids
        tokens_out = state_out.runtime.token_ids
        
        if not tokens_in:
            return True
        
        if tokens_out[:len(tokens_in)] != tokens_in:
            return False
        
        if len(tokens_out) != len(tokens_in) + delta:
            return False
        
        if len(tokens_out) != len(set(tokens_out)):
            return False
        
        return True


def make_state(seq_len: int, tokens: List[int]) -> KVCacheState:
    return KVCacheState(
        contract=KVCacheShapeContract(batch=1, heads=8, head_dim=128),
        runtime=KVRuntimeState(
            actual_sequence_length=seq_len,
            tensor_storage_shape=[1, 8, seq_len, 128],
            token_ids=tokens
        )
    )


class TestKVStateMachine:
    """Suite de tests para KV State Machine."""
    
    @pytest.fixture
    def validator(self):
        return KVStateValidator()
    
    @pytest.fixture
    def empty_state(self):
        return make_state(0, [])
    
    # Casos VÁLIDOS
    def test_initial_state(self, validator, empty_state):
        result = validator.validate(empty_state, empty_state, KVTransitionContext())
        assert result.valid
    
    def test_single_token_append(self, validator, empty_state):
        state1 = make_state(1, [101])
        result = validator.validate(empty_state, state1, KVTransitionContext())
        assert result.valid
    
    def test_two_token_append(self, validator):
        state1 = make_state(1, [101])
        state2 = make_state(2, [101, 102])
        result = validator.validate(state1, state2, KVTransitionContext())
        assert result.valid
    
    def test_prefill_batch(self, validator, empty_state):
        state128 = make_state(128, list(range(100, 228)))
        context = KVTransitionContext(max_chunk_size=128)
        result = validator.validate(empty_state, state128, context)
        assert result.valid
    
    def test_speculative_rollback(self, validator):
        """Rollback especulativo - VÁLIDO."""
        state5 = make_state(5, [101, 102, 103, 104, 105])
        state3 = make_state(3, [101, 102, 103])
        context = KVTransitionContext(shrink_reason=ShrinkReason.SPECULATIVE_ROLLBACK)
        result = validator.validate(state5, state3, context)
        assert result.valid
    
    def test_sliding_window(self, validator):
        """Sliding window - VÁLIDO."""
        state100 = make_state(100, list(range(100, 200)))
        state50 = make_state(50, list(range(150, 200)))
        context = KVTransitionContext(shrink_reason=ShrinkReason.WINDOW_EVICT)
        result = validator.validate(state100, state50, context)
        assert result.valid
    
    # Casos ILEGALES
    def test_truncate_ilegal(self, validator):
        state10 = make_state(10, list(range(100, 110)))
        state5 = make_state(5, list(range(100, 105)))
        context = KVTransitionContext(shrink_reason=ShrinkReason.NONE)
        result = validator.validate(state10, state5, context)
        assert not result.valid
    
    def test_token_swap(self, validator):
        state2 = make_state(2, [101, 102])
        state2_swap = make_state(2, [102, 101])
        result = validator.validate(state2, state2_swap, KVTransitionContext())
        assert not result.valid
    
    def test_token_duplication(self, validator):
        state2 = make_state(2, [101, 102])
        state3_dup = make_state(3, [101, 102, 102])
        result = validator.validate(state2, state3_dup, KVTransitionContext())
        assert not result.valid


def run_demo():
    print("=" * 60)
    print("KV STATE MACHINE - DEMO")
    print("=" * 60)
    
    validator = KVStateValidator()
    
    print("\n[DECODING SECUENCIAL]")
    for i in range(1, 4):
        prev = make_state(i-1, list(range(100, 100+i-1)) if i > 1 else [])
        curr = make_state(i, list(range(100, 100+i)))
        result = validator.validate(prev, curr, KVTransitionContext())
        print(f"  Step {i}: {result}")
    
    print("\n[SPECULATIVE ROLLBACK]")
    s5 = make_state(5, [101, 102, 103, 104, 105])
    s3 = make_state(3, [101, 102, 103])
    ctx = KVTransitionContext(shrink_reason=ShrinkReason.SPECULATIVE_ROLLBACK)
    print(f"  {validator.validate(s5, s3, ctx)} ✓")
    
    print("\n[TRUNCACIÓN ILEGAL]")
    s10 = make_state(10, list(range(100, 110)))
    s5_t = make_state(5, list(range(100, 105)))
    ctx_illegal = KVTransitionContext(shrink_reason=ShrinkReason.NONE)
    print(f"  {validator.validate(s10, s5_t, ctx_illegal)} ✗")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    run_demo()
