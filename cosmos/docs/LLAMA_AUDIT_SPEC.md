# LLaMA Audit Specification

**Version:** 0.4.3.2  
**Status:** ACTIVE  
**Last Updated:** 2026-07-17

---

## Overview

This document specifies the audit framework for LLaMA models in Cosmos. The framework validates model integrity, KV cache transitions, and layer-by-layer state consistency.

## Architecture Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AUDIT PIPELINE                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  BatchNorm2D                                                        │
│       │                                                             │
│       ▼                                                             │
│  MODEL_STATE                                                        │
│       │                                                             │
│       ▼                                                             │
│  LSTM                                                               │
│       │                                                             │
│       ▼                                                             │
│  RUNTIME_STATE                                                      │
│       │                                                             │
│       ▼                                                             │
│  KV CACHE                                                           │
│       │                                                             │
│       ▼                                                             │
│  TRANSFORMER BLOCK                                                  │
│       │                                                             │
│       ▼                                                             │
│  ┌─────────────┬─────────────┬─────────────┐                        │
│  │ LlamaAtten- │ LlamaMLP    │ LlamaRMSNorm│                        │
│  │ tion        │             │             │                        │
│  └─────────────┴─────────────┴─────────────┘                        │
│       │                                                             │
│       ▼                                                             │
│  CACHE_TRANSITION ───────────────────────────────────┐              │
│       │                                           │              │
│       ▼                                           │              │
│  KV CACHE UPDATE                                 │              │
│       │                                           │              │
│       ▼                                           │              │
│  KEY_STATE_OUT ◄──────────────────────────────────┘              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. KV Cache Identity

Separation between structural identity and runtime state:

```python
# Structural Identity (no depende de valores dinámicos)
KVCacheShapeContract:
  - batch: int
  - heads: int
  - head_dim: int
  - max_seq_len: int

# Runtime State (estado actual)
KVRuntimeState:
  - sequence_length: int
  - token_ids: Tuple[int, ...]
  - key_tensor_shape: List[int]
  - value_tensor_shape: List[int]
```

### 2. CACHE_TRANSITION Node

```python
@dataclass
class CacheTransition:
    transition_id: str
    transition_type: CacheTransitionType
    state_before: KVCacheState
    state_after: KVCacheState
    tokens_added: Tuple[int, ...]
    tokens_removed: Tuple[int, ...]
    shrink_reason: Optional[str]
    sri_w_before: float
    sri_w_after: float
```

### 3. Transition Types

| Type | Valid | Shrink Reason Required |
|------|-------|------------------------|
| `EXTEND` | ✓ | No |
| `SPECULATIVE_ROLLBACK` | ✓ | Yes |
| `WINDOW_EVICT` | ✓ | Yes |
| `QUANTIZE` | ✓ | Yes |
| `TRUNCATE` | ✗ | - |

### 4. SRI-W v0.4.3.2

```python
@dataclass(frozen=True)
class SRIWWeights:
    content: float = 0.45       # Fidelity of values (cosine/correlation)
    position: float = 0.30      # Positional integrity (RoPE)
    quantization: float = 0.25  # Fidelity after compression
    # lineage: REMOVED

SRI-W = α·F_content + β·F_position + γ·F_quantization
```

**Threshold:** `>= 0.999999` for native precision

## Validation Rules

### Rule 1: Append-Only with Valid Reason

```python
def validate_shrink(delta, shrink_reason):
    if delta < 0:  # Shrinkage
        if shrink_reason is None:
            return False, "SHRINK DETECTED - no reason"
        if shrink_reason == "TRUNCATE":
            return False, "ILLEGAL TRUNCATION"
        return True, f"VALID SHRINK ({shrink_reason})"
    return True, "VALID EXTEND"
```

### Rule 2: Chunk Size for Prefill

```
Δ ∈ [0, max_chunk_size]

For prefill: max_chunk_size = batch_size
For decode: max_chunk_size = 1
```

### Rule 3: SRI-W Delta

```
ΔSRI-W >= 0 (except for QUANTIZE transitions)
```

### Rule 4: Token Preservation

```
tokens_out[:len(tokens_in)] == tokens_in  # Previous tokens preserved
len(tokens_out) == len(tokens_in) + Δ     # Exactly Δ new tokens
len(tokens_out) == len(set(tokens_out))   # No duplication
```

## Valid Transition Examples

### 1. Single Token Decode

```
State: KV = [t1, t2, t3]
Input: t4
State': KV = [t1, t2, t3, t4]
Type: EXTEND
Valid: ✓
```

### 2. Speculative Rollback

```
State: KV = [t1, t2, t3, t4, t5]
Reason: draft_tokens_rejected
State': KV = [t1, t2, t3]
Type: SPECULATIVE_ROLLBACK
Valid: ✓
```

### 3. Sliding Window Eviction

```
State: KV = [t1, ..., t100]
Reason: sliding_window_4096
State': KV = [t50, ..., t100]
Type: WINDOW_EVICT
Valid: ✓
```

### 4. Prefill Batch

```
State: KV = []
Input: [t1, t2, ..., t128]
State': KV = [t1, t2, ..., t128]
Type: EXTEND
Δ: 128
Valid: ✓
```

## Invalid Transition Examples

### 1. Truncation Without Reason

```
State: KV = [t1, ..., t10]
State': KV = [t1, ..., t5]
Reason: None
Type: TRUNCATE
Valid: ✗ (REJECT)
```

### 2. Token Swap

```
State: KV = [t1, t2]
State': KV = [t2, t1]
Type: EXTEND (Δ = 0)
Valid: ✗ (REORDER DETECTED)
```

### 3. Token Duplication

```
State: KV = [t1, t2]
State': KV = [t1, t2, t2]
Type: EXTEND (Δ = 1)
Valid: ✗ (DUPLICATION DETECTED)
```

### 4. Token Loss

```
State: KV = [t1, t2, t3]
State': KV = [t1, t3]
Type: EXTEND (Δ = -1)
Reason: None
Valid: ✗ (TOKEN LOSS)
```

## Audit Suite

### test_kv_state_machine.py

Tests KV state transitions:

- `test_initial_state`
- `test_single_token_append`
- `test_two_token_append`
- `test_prefill_batch`
- `test_chunked_prefill`
- `test_speculative_rollback` ✓
- `test_sliding_window` ✓
- `test_truncate_ilegal` ✗
- `test_token_swap` ✗
- `test_token_duplication` ✗

### test_llama_attention.py

Tests attention layer + CACHE_TRANSITION:

- `test_initial_cache`
- `test_extend_single_token`
- `test_extend_multiple_tokens`
- `test_speculative_rollback`
- `test_window_eviction`
- `test_quantization_fp16_to_int8`
- `test_chain_validation`
- `test_delta_sri_w_tracking`

### test_llama_decoder_layer.py

Tests decoder layer:

- `test_single_layer_pass`
- `test_hidden_state_mismatch`
- `test_kv_cache_disabled`
- `test_pipeline_4_layers`
- `test_last_layer_flag`

### test_llama_full.py

Tests end-to-end:

- `test_config_validation`
- `test_invalid_config`
- `test_token_sequence_valid`
- `test_token_sequence_invalid_positions`
- `test_token_sequence_unk_token`
- `test_forward_pass_full`
- `test_forward_pass_prefill`
- `test_forward_pass_single_token`

## Run Audit Suite

```bash
# All tests
python -m pytest cosmos/tests/ -v

# Specific test file
python -m pytest cosmos/tests/test_llama_full.py -v

# Single test
python -m pytest cosmos/tests/test_llama_full.py::TestLlamaFullAudit::test_forward_pass_full -v

# With coverage
python -m pytest cosmos/tests/ --cov=cosmos --cov-report=term-missing
```

## Metrics

| Metric | Description |
|--------|-------------|
| `sri_w_before` | SRI-W before transition |
| `sri_w_after` | SRI-W after transition |
| `delta_sri_w` | Change in SRI-W |
| `num_layers` | Number of transformer layers |
| `num_cache_states` | Number of KV cache states |
| `input_length` | Length of input sequence |

## Future Enhancements

- [ ] Real tensor validation (not simulated shapes)
- [ ] Cosine similarity computation for F_content
- [ ] RoPE angle verification for F_position
- [ ] Integration with HuggingFace Transformers
- [ ] Integration with vLLM PagedAttention
- [ ] Streaming inference support

---

**Author:** Luis Alberto Burciaga Miker  
**Co-authored-by:** OpenHands <openhands@all-hands.dev>
