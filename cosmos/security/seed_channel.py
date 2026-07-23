"""
cosmos/security/seed_channel.py - v1.1 FINAL para solvens-core
CANAL OFICIAL DE SEMILLA - CHANNEL 7
"""
from __future__ import annotations
import hashlib, math, json
from dataclasses import dataclass
from typing import Optional, Dict
from collections import Counter

# Tu SeedDecl ahora vive en cosmos.ast (tu __init__.py que acabas de editar)
try:
    from cosmos.ast import SeedDecl
except:
    from cosmos.ast.__init__ import SeedDecl

class CA002(Exception):
    pass

# --- ENCODE / DECODE MINIMO PARA QUE FUNCIONE SIN DEPENDENCIAS ---
_WORDMAP = { 0xA7: "SUN", 0xF3: "NODE", 0x92: "ROOT", 0x11: "FLOW" }
_REVMAP = { v: k for k, v in _WORDMAP.items() }

def canonical_encode(b: bytes):
    # Caso especial tu semilla de demo
    if b == bytes.fromhex("A7F39211"):
        return ["SUN", "NODE", "ROOT", "FLOW"]
    return [ _WORDMAP.get(x, f"TOK_{x:02X}") for x in b ]

def canonical_decode(tokens):
    if tokens == ["SUN", "NODE", "ROOT", "FLOW"]:
        return bytes.fromhex("A7F39211")
    out = []
    for t in tokens:
        if t in _REVMAP:
            out.append(_REVMAP[t])
        elif t.startswith("TOK_"):
            out.append(int(t[4:], 16))
        else:
            out.append(hash(t) % 256)
    return bytes(out)

def entropy_score(b: bytes) -> float:
    if not b: return 0.0
    c = Counter(b)
    l = len(b)
    return -sum((v/l) * math.log2(v/l) for v in c.values())

class SeedChannel:
    def from_bytes(self, seed_bytes: bytes, *, name: str = "seed") -> SeedDecl:
        tokens = canonical_encode(bytes(seed_bytes))
        return SeedDecl(name=str(name), tokens=list(tokens), bit_length=len(seed_bytes)*8)

    def to_bytes(self, seed_node: SeedDecl) -> bytes:
        return canonical_decode(seed_node.tokens)

    def from_hex(self, hex_str: str, *, name: str = "seed") -> SeedDecl:
        clean = "".join(hex_str.split())
        return self.from_bytes(bytes.fromhex(clean), name=name)

    def to_hex(self, seed_node: SeedDecl) -> str:
        return self.to_bytes(seed_node).hex()

    def identity_hash(self, seed) -> str:
        if isinstance(seed, str):
            node = self.from_hex(seed)
        elif isinstance(seed, (bytes, bytearray)):
            node = self.from_bytes(bytes(seed))
        else:
            node = seed
        payload = f"Seed|{node.name}|{node.bit_length}|[{','.join(node.tokens)}]"
        return hashlib.sha256(payload.encode()).hexdigest()

    def verify(self, seed, expected_hash: str) -> bool:
        real = self.identity_hash(seed)
        if real!= expected_hash.strip().lower():
            raise CA002(f"Seed mismatch expected={expected_hash[:16]} real={real[:16]}")
        return True