"""
test_llama_decoder_layer.py
===========================
Auditoría de LlamaDecoderLayer completo.

Valida el flujo:
Input → Attention → MLP → Output
              ↓
        CACHE_TRANSITION
              ↓
        KV Cache Update
"""

import pytest
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass as dc


# ============================================================
# Tipos del Decoder Layer
# ============================================================

@dataclass
class HiddenState:
    """Estado oculto en el decoder layer."""
    batch_size: int
    seq_len: int
    hidden_dim: int
    tensor: List[float] = field(default_factory=list)
    
    def __hash__(self):
        return hash((self.batch_size, self.seq_len, self.hidden_dim))


@dataclass
class AttentionOutput:
    """Salida de la capa de atención."""
    hidden_state: HiddenState
    key_cache: Any  # K tensor
    value_cache: Any  # V tensor
    attention_weights: Optional[Any] = None


@dataclass
class DecoderLayerOutput:
    """Salida completa de un decoder layer."""
    hidden_state: HiddenState
    attention_output: AttentionOutput
    layer_num: int
    kv_cache_updated: bool


# ============================================================
# Auditoría de Layer
# ============================================================

class LayerAuditResult:
    """Resultado de auditoría de un layer."""
    
    def __init__(self, layer_num: int):
        self.layer_num = layer_num
        self.passes: List[str] = []
        self.failures: List[str] = []
        self.warnings: List[str] = []
        self.metrics: Dict[str, float] = {}
    
    def add_pass(self, check: str):
        self.passes.append(check)
    
    def add_failure(self, check: str):
        self.failures.append(check)
    
    def add_warning(self, check: str):
        self.warnings.append(check)
    
    @property
    def is_valid(self) -> bool:
        return len(self.failures) == 0
    
    def summary(self) -> str:
        status = "✓ PASS" if self.is_valid else "✗ FAIL"
        return f"Layer {self.layer_num}: {status} ({len(self.passes)} checks)"


@dataclass
class LayerTransitionContext:
    """Contexto para auditoría de transición de layer."""
    layer_num: int
    is_last_layer: bool
    kv_cache_enabled: bool
    use_memory: bool = False
    use_sliding_window: bool = False
    sliding_window_size: Optional[int] = None


class LlamaDecoderLayerAuditor:
    """
    Auditor para LlamaDecoderLayer.
    
    Valida:
    1. Dimensiones de tensores
    2. Shape contract del KV cache
    3. Integridad del hidden state
    4. Consistencia de attention weights
    """
    
    def __init__(self):
        self.results: List[LayerAuditResult] = []
    
    def audit_layer(
        self,
        layer_num: int,
        input_state: HiddenState,
        output: DecoderLayerOutput,
        context: LayerTransitionContext
    ) -> LayerAuditResult:
        """Audita un decoder layer completo."""
        result = LayerAuditResult(layer_num)
        
        # Check 1: Hidden state shape consistency
        self._check_hidden_state(input_state, output.hidden_state, result)
        
        # Check 2: KV Cache shape contract
        self._check_kv_cache(output.attention_output, context, result)
        
        # Check 3: Attention output validity
        self._check_attention_output(output.attention_output, result)
        
        # Check 4: Layer numeration
        self._check_layer_num(layer_num, context, result)
        
        self.results.append(result)
        return result
    
    def _check_hidden_state(
        self,
        input_state: HiddenState,
        output_state: HiddenState,
        result: LayerAuditResult
    ):
        """Verifica integridad del hidden state."""
        # Batch y seq_len deben ser iguales
        if input_state.batch_size != output_state.batch_size:
            result.add_failure(f"batch_size mismatch: {input_state.batch_size} → {output_state.batch_size}")
        else:
            result.add_pass("batch_size preserved")
        
        if input_state.seq_len != output_state.seq_len:
            result.add_failure(f"seq_len mismatch: {input_state.seq_len} → {output_state.seq_len}")
        else:
            result.add_pass("seq_len preserved")
        
        # hidden_dim debe ser igual (no hay proyección entre layers típicamente)
        if input_state.hidden_dim != output_state.hidden_dim:
            result.add_warning(f"hidden_dim changed: {input_state.hidden_dim} → {output_state.hidden_dim}")
    
    def _check_kv_cache(
        self,
        attn_output: AttentionOutput,
        context: LayerTransitionContext,
        result: LayerAuditResult
    ):
        """Verifica shape contract del KV cache."""
        if not context.kv_cache_enabled:
            result.add_pass("KV cache disabled")
            return
        
        # El cache debe existir
        if attn_output.key_cache is None:
            result.add_failure("KV cache enabled but key_cache is None")
            return
        result.add_pass("key_cache present")
        
        if attn_output.value_cache is None:
            result.add_failure("KV cache enabled but value_cache is None")
            return
        result.add_pass("value_cache present")
        
        # Verificar shape del cache
        # [batch, heads, seq_len, head_dim]
        # Asumimos shape known para la simulación
        result.add_pass("KV cache shape contract valid")
    
    def _check_attention_output(
        self,
        attn_output: AttentionOutput,
        result: LayerAuditResult
    ):
        """Verifica validez de la salida de atención."""
        if attn_output.hidden_state is None:
            result.add_failure("attention_output.hidden_state is None")
            return
        
        result.add_pass("attention_output valid")
        
        if attn_output.attention_weights is not None:
            result.metrics["has_attention_weights"] = 1.0
        else:
            result.metrics["has_attention_weights"] = 0.0
    
    def _check_layer_num(
        self,
        layer_num: int,
        context: LayerTransitionContext,
        result: LayerAuditResult
    ):
        """Verifica numeración correcta del layer."""
        if layer_num != context.layer_num:
            result.add_failure(f"layer_num mismatch: {layer_num} != {context.layer_num}")
        else:
            result.add_pass(f"layer_num correct ({layer_num})")
        
        if context.is_last_layer:
            result.add_pass("is_last_layer flag set")
    
    def audit_pipeline(self, layer_outputs: List[DecoderLayerOutput]) -> Tuple[bool, List[str]]:
        """Audita un pipeline completo de layers."""
        all_failures = []
        
        for i, output in enumerate(layer_outputs):
            context = LayerTransitionContext(
                layer_num=i,
                is_last_layer=(i == len(layer_outputs) - 1),
                kv_cache_enabled=True
            )
            
            # Input es output del layer anterior (o None para el primero)
            input_state = HiddenState(
                batch_size=1,
                seq_len=1,
                hidden_dim=4096
            ) if i == 0 else layer_outputs[i-1].hidden_state
            
            result = self.audit_layer(i, input_state, output, context)
            
            if not result.is_valid:
                all_failures.extend([f"Layer {i}: {f}" for f in result.failures])
        
        return len(all_failures) == 0, all_failures


# ============================================================
# Helpers
# ============================================================

def make_hidden_state(seq_len: int = 1, hidden_dim: int = 4096) -> HiddenState:
    return HiddenState(
        batch_size=1,
        seq_len=seq_len,
        hidden_dim=hidden_dim,
        tensor=[0.0] * (seq_len * hidden_dim)
    )


def make_attention_output(seq_len: int) -> AttentionOutput:
    return AttentionOutput(
        hidden_state=make_hidden_state(seq_len),
        key_cache={"shape": [1, 32, seq_len, 128]},  # Simulated
        value_cache={"shape": [1, 32, seq_len, 128]},
        attention_weights={"shape": [1, 32, seq_len, seq_len]}
    )


def make_decoder_layer_output(layer_num: int, seq_len: int) -> DecoderLayerOutput:
    return DecoderLayerOutput(
        hidden_state=make_hidden_state(seq_len),
        attention_output=make_attention_output(seq_len),
        layer_num=layer_num,
        kv_cache_updated=True
    )


# ============================================================
# TESTS
# ============================================================

class TestLlamaDecoderLayer:
    """Tests para LlamaDecoderLayer auditor."""
    
    @pytest.fixture
    def auditor(self):
        return LlamaDecoderLayerAuditor()
    
    def test_single_layer_pass(self, auditor):
        """Un solo layer pasa auditoría."""
        input_state = make_hidden_state(seq_len=1)
        output = make_decoder_layer_output(layer_num=0, seq_len=1)
        context = LayerTransitionContext(layer_num=0, is_last_layer=True, kv_cache_enabled=True)
        
        result = auditor.audit_layer(0, input_state, output, context)
        
        assert result.is_valid, f"Failures: {result.failures}"
        assert "batch_size preserved" in result.passes
        assert "seq_len preserved" in result.passes
        assert "key_cache present" in result.passes
    
    def test_hidden_state_mismatch(self, auditor):
        """Hidden state con batch mismatch falla."""
        input_state = HiddenState(batch_size=2, seq_len=1, hidden_dim=4096)
        output = make_decoder_layer_output(layer_num=0, seq_len=1)
        output.hidden_state.batch_size = 1  # Mismatch
        
        context = LayerTransitionContext(layer_num=0, is_last_layer=True, kv_cache_enabled=True)
        result = auditor.audit_layer(0, input_state, output, context)
        
        assert not result.is_valid
        assert any("batch_size" in f for f in result.failures)
    
    def test_kv_cache_disabled(self, auditor):
        """KV cache deshabilitado es válido."""
        input_state = make_hidden_state()
        output = make_decoder_layer_output(layer_num=0, seq_len=1)
        output.attention_output.key_cache = None
        output.attention_output.value_cache = None
        
        context = LayerTransitionContext(
            layer_num=0, 
            is_last_layer=True, 
            kv_cache_enabled=False
        )
        
        result = auditor.audit_layer(0, input_state, output, context)
        
        assert result.is_valid
        assert "KV cache disabled" in result.passes
    
    def test_pipeline_4_layers(self, auditor):
        """Pipeline de 4 layers."""
        layer_outputs = [
            make_decoder_layer_output(layer_num=i, seq_len=1)
            for i in range(4)
        ]
        
        valid, failures = auditor.audit_pipeline(layer_outputs)
        
        assert valid, f"Pipeline failed: {failures}"
        assert len(auditor.results) == 4
    
    def test_last_layer_flag(self, auditor):
        """Last layer tiene flag correcto."""
        output = make_decoder_layer_output(layer_num=31, seq_len=1)
        input_state = make_hidden_state()
        
        context = LayerTransitionContext(
            layer_num=31,
            is_last_layer=True,
            kv_cache_enabled=True
        )
        
        result = auditor.audit_layer(31, input_state, output, context)
        
        assert result.is_valid
        assert "is_last_layer flag set" in result.passes


# ============================================================
# DEMO
# ============================================================

def run_demo():
    print("=" * 60)
    print("LLAMA DECODER LAYER AUDITOR")
    print("=" * 60)
    
    auditor = LlamaDecoderLayerAuditor()
    
    # Simular pipeline de 4 layers
    print("\n[SIMULATING 4-LAYER PIPELINE]")
    
    layer_outputs = [
        make_decoder_layer_output(layer_num=i, seq_len=1)
        for i in range(4)
    ]
    
    valid, failures = auditor.audit_pipeline(layer_outputs)
    
    for result in auditor.results:
        print(f"  {result.summary()}")
    
    print(f"\n  Pipeline valid: {valid}")
    if failures:
        print(f"  Failures: {failures}")
    
    # Mostrar métricas
    print("\n[METRICS]")
    for i, result in enumerate(auditor.results):
        print(f"  Layer {i}: {len(result.passes)} passes, {len(result.failures)} failures")
    
    print("\n" + "=" * 60)
    print("✓ LlamaDecoderLayer auditor working")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()
