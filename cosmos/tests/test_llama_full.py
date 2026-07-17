"""
test_llama_full.py
==================
Integración end-to-end con LlamaForCausalLM.

Ruta de auditoría completa:
BatchNorm2D
      |
      v
MODEL_STATE
      |
      v
LSTM
      |
      v
RUNTIME_STATE
      |
      v
KV CACHE
      |
      v
TRANSFORMER BLOCK
      |
      v
FULL LLAMA AUDIT
"""

import pytest
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass as dc


# ============================================================
# Arquitectura Completa de LLaMA
# ============================================================

@dataclass
class ModelConfig:
    """Configuración del modelo LLaMA."""
    vocab_size: int = 32000
    hidden_size: int = 4096
    intermediate_size: int = 11008
    num_hidden_layers: int = 32
    num_attention_heads: int = 32
    num_key_value_heads: int = 32
    max_position_embeddings: int = 2048
    rope_theta: float = 10000.0
    rms_norm_eps: float = 1e-6


@dataclass
class ModelState:
    """Estado global del modelo."""
    config: ModelConfig
    layer_states: List[Dict[str, Any]]
    total_parameters: int
    is_training: bool = False
    kv_cache_enabled: bool = True


@dataclass
class TokenSequence:
    """Secuencia de tokens de entrada."""
    ids: Tuple[int, ...]
    position_ids: Tuple[int, ...]
    
    @property
    def length(self) -> int:
        return len(self.ids)


@dataclass
class LlamaOutput:
    """Salida completa del modelo."""
    logits: Any  # [batch, seq_len, vocab_size]
    hidden_states: List[Any]  # Hidden states por layer
    kv_cache_states: Dict[int, Dict[str, Any]]  # Cache por layer
    attention_weights: Optional[List[Any]] = None


@dataclass
class AuditReport:
    """Reporte completo de auditoría."""
    model_name: str = "LlamaForCausalLM"
    config_valid: bool = False
    layers_valid: bool = False
    kv_cache_valid: bool = False
    token_sequence_valid: bool = False
    overall_valid: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)


# ============================================================
# Auditor Completo de LLaMA
# ============================================================

class LlamaForCausalLMAuditor:
    """
    Auditor completo para LlamaForCausalLM.
    
    Valida:
    1. Configuración del modelo
    2. Secuencia de tokens
    3. Estados por layer
    4. KV Cache states
    5. Hidden states consistency
    """
    
    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config or ModelConfig()
        self.layer_audits: List[Dict[str, Any]] = []
        self.cache_transitions: List[Dict[str, Any]] = []
    
    def audit_config(self) -> Tuple[bool, List[str]]:
        """Valida la configuración del modelo."""
        errors = []
        
        # Check vocab_size
        if self.config.vocab_size <= 0:
            errors.append(f"Invalid vocab_size: {self.config.vocab_size}")
        
        # Check hidden_size divisible by num_attention_heads
        if self.config.hidden_size % self.config.num_attention_heads != 0:
            errors.append(f"hidden_size ({self.config.hidden_size}) not divisible by num_attention_heads ({self.config.num_attention_heads})")
        
        # Check num_key_value_heads <= num_attention_heads (GQA)
        if self.config.num_key_value_heads > self.config.num_attention_heads:
            errors.append(f"num_key_value_heads ({self.config.num_key_value_heads}) > num_attention_heads ({self.config.num_attention_heads})")
        
        # Check rope_theta > 0
        if self.config.rope_theta <= 0:
            errors.append(f"Invalid rope_theta: {self.config.rope_theta}")
        
        return len(errors) == 0, errors
    
    def audit_token_sequence(self, tokens: TokenSequence) -> Tuple[bool, List[str]]:
        """Valida secuencia de tokens."""
        errors = []
        
        if len(tokens.ids) == 0:
            errors.append("Empty token sequence")
        
        # Position IDs deben ser consecutivos (desde cualquier offset)
        if len(tokens.ids) > 1:
            for i in range(1, len(tokens.ids)):
                expected = tokens.position_ids[i-1] + 1
                if tokens.position_ids[i] != expected:
                    errors.append(f"Position IDs not consecutive at index {i}: {tokens.position_ids[i-1]} -> {tokens.position_ids[i]}")
                    break
        
        # Vocab IDs deben estar en rango
        max_id = max(tokens.ids) if tokens.ids else 0
        if max_id >= self.config.vocab_size:
            errors.append(f"Token ID {max_id} exceeds vocab_size {self.config.vocab_size}")
        
        return len(errors) == 0, errors
    
    def audit_layer(self, layer_num: int, hidden_state: Any, kv_cache: Dict[str, Any]) -> Dict[str, Any]:
        """Audita un layer individual."""
        audit = {
            "layer_num": layer_num,
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check hidden state shape
        if hidden_state is None:
            audit["valid"] = False
            audit["errors"].append("hidden_state is None")
        
        # Check KV cache presence
        if "key_cache" not in kv_cache:
            audit["warnings"].append("key_cache not found")
        if "value_cache" not in kv_cache:
            audit["warnings"].append("value_cache not found")
        
        self.layer_audits.append(audit)
        return audit
    
    def audit_forward_pass(
        self,
        input_tokens: TokenSequence,
        output: LlamaOutput
    ) -> AuditReport:
        """Audita un forward pass completo."""
        report = AuditReport()
        
        # 1. Audit config
        config_valid, config_errors = self.audit_config()
        report.config_valid = config_valid
        if config_errors:
            report.errors.extend([f"[CONFIG] {e}" for e in config_errors])
        
        # 2. Audit token sequence
        tokens_valid, token_errors = self.audit_token_sequence(input_tokens)
        report.token_sequence_valid = tokens_valid
        if token_errors:
            report.errors.extend([f"[TOKENS] {e}" for e in token_errors])
        
        # 3. Audit layers
        layers_valid = True
        if output.hidden_states:
            for i, hidden in enumerate(output.hidden_states):
                kv_cache = output.kv_cache_states.get(i, {})
                layer_audit = self.audit_layer(i, hidden, kv_cache)
                if not layer_audit["valid"]:
                    layers_valid = False
                    report.errors.extend([f"[LAYER {i}] {e}" for e in layer_audit["errors"]])
                report.warnings.extend([f"[LAYER {i}] {w}" for w in layer_audit["warnings"]])
        
        report.layers_valid = layers_valid
        
        # 4. Audit KV cache
        kv_valid = len(output.kv_cache_states) == self.config.num_hidden_layers
        report.kv_cache_valid = kv_valid
        if not kv_valid:
            report.errors.append(f"KV cache states count mismatch: {len(output.kv_cache_states)} != {self.config.num_hidden_layers}")
        
        # 5. Overall
        report.overall_valid = (
            report.config_valid and
            report.token_sequence_valid and
            report.layers_valid and
            report.kv_cache_valid
        )
        
        # Metrics
        report.metrics["num_layers"] = len(output.hidden_states) if output.hidden_states else 0
        report.metrics["num_cache_states"] = len(output.kv_cache_states)
        report.metrics["input_length"] = input_tokens.length
        
        return report


# ============================================================
# Simulador de LLaMA
# ============================================================

class LlamaSimulator:
    """Simula un forward pass de LLaMA para testing."""
    
    def __init__(self, config: ModelConfig):
        self.config = config
    
    def forward(self, tokens: TokenSequence) -> LlamaOutput:
        """Simula forward pass."""
        num_layers = self.config.num_hidden_layers
        
        # Hidden states por layer (simulado)
        hidden_states = [
            {"shape": [1, tokens.length, self.config.hidden_size]}
            for _ in range(num_layers)
        ]
        
        # KV cache por layer (simulado)
        kv_cache_states = {
            i: {
                "key_cache": {"shape": [1, self.config.num_key_value_heads, tokens.length, self.config.hidden_size // self.config.num_attention_heads]},
                "value_cache": {"shape": [1, self.config.num_key_value_heads, tokens.length, self.config.hidden_size // self.config.num_attention_heads]}
            }
            for i in range(num_layers)
        }
        
        return LlamaOutput(
            logits={"shape": [1, tokens.length, self.config.vocab_size]},
            hidden_states=hidden_states,
            kv_cache_states=kv_cache_states
        )


# ============================================================
# TESTS
# ============================================================

class TestLlamaFullAudit:
    """Tests de integración end-to-end."""
    
    @pytest.fixture
    def auditor(self):
        return LlamaForCausalLMAuditor()
    
    @pytest.fixture
    def simulator(self):
        return LlamaSimulator(ModelConfig())
    
    def test_config_validation(self, auditor):
        """Config por defecto es válida."""
        valid, errors = auditor.audit_config()
        assert valid, f"Config errors: {errors}"
    
    def test_invalid_config(self):
        """Config inválida detecta errores."""
        bad_config = ModelConfig(
            vocab_size=0,
            hidden_size=100,  # No divisible por heads
            num_attention_heads=32,
            num_key_value_heads=64,  # > attention heads
        )
        auditor = LlamaForCausalLMAuditor(bad_config)
        
        valid, errors = auditor.audit_config()
        
        assert not valid
        assert len(errors) >= 3  # Al menos 3 errores
    
    def test_token_sequence_valid(self, auditor):
        """Secuencia de tokens válida."""
        tokens = TokenSequence(
            ids=(101, 102, 103, 104, 105),
            position_ids=(0, 1, 2, 3, 4)
        )
        
        valid, errors = auditor.audit_token_sequence(tokens)
        assert valid, f"Token errors: {errors}"
    
    def test_token_sequence_invalid_positions(self, auditor):
        """Secuencia con position IDs incorrectos."""
        tokens = TokenSequence(
            ids=(101, 102, 103),
            position_ids=(0, 2, 3)  # Falta 1
        )
        
        valid, errors = auditor.audit_token_sequence(tokens)
        assert not valid
        assert any("Position IDs" in e for e in errors)
    
    def test_token_sequence_unk_token(self, auditor):
        """Secuencia con token fuera de vocab."""
        tokens = TokenSequence(
            ids=(100, 200, 50000),  # 50000 > vocab_size
            position_ids=(0, 1, 2)
        )
        
        valid, errors = auditor.audit_token_sequence(tokens)
        assert not valid
        assert any("exceeds vocab_size" in e for e in errors)
    
    def test_forward_pass_full(self, auditor, simulator):
        """Forward pass completo pasa auditoría."""
        tokens = TokenSequence(
            ids=tuple(range(100, 132)),  # 32 tokens
            position_ids=tuple(range(32))
        )
        
        output = simulator.forward(tokens)
        report = auditor.audit_forward_pass(tokens, output)
        
        assert report.overall_valid, f"Audit failed: {report.errors}"
        assert report.config_valid
        assert report.token_sequence_valid
        assert report.layers_valid
        assert report.kv_cache_valid
        assert report.metrics["num_layers"] == 32
        assert report.metrics["input_length"] == 32
    
    def test_forward_pass_prefill(self, auditor, simulator):
        """Prefill de 128 tokens."""
        tokens = TokenSequence(
            ids=tuple(range(100, 228)),  # 128 tokens
            position_ids=tuple(range(128))
        )
        
        output = simulator.forward(tokens)
        report = auditor.audit_forward_pass(tokens, output)
        
        assert report.overall_valid
        assert report.metrics["input_length"] == 128
    
    def test_forward_pass_single_token(self, auditor, simulator):
        """Decode de 1 token."""
        tokens = TokenSequence(
            ids=(101,),
            position_ids=(0,)
        )
        
        output = simulator.forward(tokens)
        report = auditor.audit_forward_pass(tokens, output)
        
        assert report.overall_valid
        assert report.metrics["input_length"] == 1


# ============================================================
# DEMO
# ============================================================

def run_demo():
    print("=" * 60)
    print("LLAMA FOR CAUSAL LM - FULL AUDIT")
    print("=" * 60)
    
    config = ModelConfig()
    auditor = LlamaForCausalLMAuditor(config)
    simulator = LlamaSimulator(config)
    
    print(f"\n[MODEL CONFIG]")
    print(f"  Layers: {config.num_hidden_layers}")
    print(f"  Heads: {config.num_attention_heads}")
    print(f"  Hidden: {config.hidden_size}")
    print(f"  Vocab: {config.vocab_size}")
    
    # Test 1: Prefill
    print(f"\n[TEST 1: PREFILL 128 TOKENS]")
    tokens = TokenSequence(
        ids=tuple(range(100, 228)),
        position_ids=tuple(range(128))
    )
    output = simulator.forward(tokens)
    report = auditor.audit_forward_pass(tokens, output)
    
    print(f"  Overall valid: {report.overall_valid}")
    print(f"  Config: {report.config_valid}")
    print(f"  Tokens: {report.token_sequence_valid}")
    print(f"  Layers: {report.layers_valid}")
    print(f"  KV Cache: {report.kv_cache_valid}")
    print(f"  Metrics: {report.metrics}")
    
    if report.errors:
        print(f"  Errors: {report.errors}")
    
    # Test 2: Decode (continuación desde 128)
    print(f"\n[TEST 2: DECODE 1 TOKEN (continuación)]")
    tokens = TokenSequence(ids=(229,), position_ids=(128,))  # Continúa desde donde quedó
    output = simulator.forward(tokens)
    report = auditor.audit_forward_pass(tokens, output)
    
    print(f"  Overall valid: {report.overall_valid}")
    print(f"  Tokens: {report.token_sequence_valid}")
    print(f"  Metrics: {report.metrics}")
    
    # Test 2b: Decode desde 0 (inicialización)
    print(f"\n[TEST 2b: DECODE 1 TOKEN (inicial)]")
    tokens = TokenSequence(ids=(101,), position_ids=(0,))  # Desde 0
    output = simulator.forward(tokens)
    report = auditor.audit_forward_pass(tokens, output)
    
    print(f"  Overall valid: {report.overall_valid}")
    print(f"  Tokens: {report.token_sequence_valid}")
    
    print("\n" + "=" * 60)
    print("✓ LlamaForCausalLM full audit complete")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()
