"""
Hyperdimensional Vector Symbolic Architecture (HDC / VSA) Engine for AI Ontologies.
Provides O(1) holographic associative memory, compositional unbinding, and noise-tolerant reasoning
in high-dimensional bipolar vector space {-1, +1}^D without external library dependencies.
"""

import math
import random
from typing import Dict, List, Tuple, Any, Optional


class HDVector:
    """Bipolar Hyperdimensional Vector in {-1, +1}^D."""
    __slots__ = ('dim', 'values')

    def __init__(self, values: List[int], dim: Optional[int] = None):
        self.values = values
        self.dim = len(values) if dim is None else dim

    @classmethod
    def random_deterministic(cls, name: str, dim: int = 2048) -> 'HDVector':
        """Generate a deterministic pseudo-random bipolar vector seeded by string name."""
        seed_val = 0
        for char in name:
            seed_val = (seed_val * 31 + ord(char)) & 0xFFFFFFFF
        rng = random.Random(seed_val)
        vals = [1 if rng.random() >= 0.5 else -1 for _ in range(dim)]
        return cls(vals, dim)

    def bind(self, other: 'HDVector') -> 'HDVector':
        """
        Binding operation (XOR in binary / element-wise multiplication in bipolar).
        u * v: forms a new quasi-orthogonal vector representing association.
        Self-inverse property: u * (u * v) = v (exact unbinding).
        """
        if self.dim != other.dim:
            raise ValueError(f"Vector dimensions do not match: {self.dim} != {other.dim}")
        return HDVector([a * b for a, b in zip(self.values, other.values)], self.dim)

    def bundle(self, others: List['HDVector']) -> 'HDVector':
        """
        Bundling operation (Superposition / Majority voting).
        Combines multiple vectors into a single vector that remains similar to all constituents.
        """
        all_vecs = [self] + others
        count = len(all_vecs)
        accum = [0] * self.dim
        for v in all_vecs:
            for i in range(self.dim):
                accum[i] += v.values[i]

        # Tie-breaker deterministic pseudo-random
        result = []
        for i, total in enumerate(accum):
            if total > 0:
                result.append(1)
            elif total < 0:
                result.append(-1)
            else:
                result.append(1 if (i % 2 == 0) else -1)
        return HDVector(result, self.dim)

    def permute(self, k: int = 1) -> 'HDVector':
        """
        Permutation operation (Cyclic shift by k positions).
        Used to represent sequence, roles, or temporal order.
        """
        shift = k % self.dim
        if shift == 0:
            return HDVector(list(self.values), self.dim)
        new_vals = self.values[-shift:] + self.values[:-shift]
        return HDVector(new_vals, self.dim)

    def inverse_permute(self, k: int = 1) -> 'HDVector':
        """Inverse permutation (shift back by -k positions)."""
        return self.permute(-k)

    def dot(self, other: 'HDVector') -> int:
        """Inner product between two bipolar vectors."""
        return sum(a * b for a, b in zip(self.values, other.values))

    def cosine_similarity(self, other: 'HDVector') -> float:
        """Normalized similarity in [-1.0, 1.0]."""
        return self.dot(other) / float(self.dim)

    def corrupt(self, noise_ratio: float, seed: int = 42) -> 'HDVector':
        """Corrupt vector by randomly flipping a fraction of bits."""
        rng = random.Random(seed)
        num_flips = int(self.dim * max(0.0, min(1.0, noise_ratio)))
        flip_indices = set(rng.sample(range(self.dim), num_flips))
        corrupted = [-v if i in flip_indices else v for i, v in enumerate(self.values)]
        return HDVector(corrupted, self.dim)


class HyperdimensionalVSA:
    """
    Hyperdimensional Vector Symbolic Architecture Engine for Knowledge Graphs.
    Transforms RDF triples into holographic vectors and enables O(1) unbinding queries.
    """

    def __init__(self, dim: int = 2048):
        self.dim = dim
        self.atom_memory: Dict[str, HDVector] = {}

    def get_atom(self, name: str) -> HDVector:
        """Retrieve or create an atomic hypervector for an ontology entity or relation."""
        if name not in self.atom_memory:
            self.atom_memory[name] = HDVector.random_deterministic(name, self.dim)
        return self.atom_memory[name]

    def encode_triple(self, s: str, p: str, o: str) -> HDVector:
        """
        Encodes a triple (s, p, o) into a single hypervector using permutation roles:
        vec(s, p, o) = Pi^0(s) * Pi^1(p) * Pi^2(o)
        """
        v_s = self.get_atom(s).permute(0)
        v_p = self.get_atom(p).permute(1)
        v_o = self.get_atom(o).permute(2)
        return v_s.bind(v_p).bind(v_o)

    def encode_graph(self, triples: List[Tuple[str, str, str]]) -> HDVector:
        """Encodes an entire knowledge graph into a single holographic hypervector."""
        if not triples:
            return HDVector([1] * self.dim, self.dim)
        triple_vecs = [self.encode_triple(s, p, o) for s, p, o in triples]
        return triple_vecs[0].bundle(triple_vecs[1:])

    def query_object(self, graph_vec: HDVector, s: str, p: str, candidates: Optional[List[str]] = None) -> List[Tuple[str, float]]:
        """
        Holographic O(1) Query: Given (s, p, ?o) and graph vector G, unbinds ?o:
        ?o ~ Pi^(-2)[ G * (Pi^0(s) * Pi^1(p)) ]
        Returns ranked list of candidate entities by cosine similarity.
        """
        v_s = self.get_atom(s).permute(0)
        v_p = self.get_atom(p).permute(1)
        query_key = v_s.bind(v_p)

        # Unbind from composite graph vector
        unbound = graph_vec.bind(query_key).inverse_permute(2)

        candidate_keys = candidates if candidates else list(self.atom_memory.keys())
        scores = []
        for cand in candidate_keys:
            sim = unbound.cosine_similarity(self.get_atom(cand))
            scores.append((cand, round(sim, 4)))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

    def solve_analogy(self, a: str, b: str, c: str, candidates: Optional[List[str]] = None) -> List[Tuple[str, float]]:
        """
        Vector Symbolic Analogy: "A is to B as C is to ?"
        Transformation operator T = B * A
        Target D ~ C * T = C * (B * A)
        """
        v_a = self.get_atom(a)
        v_b = self.get_atom(b)
        v_c = self.get_atom(c)
        target = v_c.bind(v_b.bind(v_a))

        candidate_keys = candidates if candidates else [k for k in self.atom_memory.keys() if k not in {a, b, c}]
        scores = []
        for cand in candidate_keys:
            sim = target.cosine_similarity(self.get_atom(cand))
            scores.append((cand, round(sim, 4)))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

    def benchmark_noise_resilience(self, s: str, p: str, o: str, noise_levels: Optional[List[float]] = None) -> Dict[str, Any]:
        """Tests holographic reconstruction fidelity across various bit corruption ratios."""
        levels = noise_levels or [0.1, 0.25, 0.4, 0.5]
        triple_vec = self.encode_triple(s, p, o)

        results = {}
        for noise in levels:
            corrupted = triple_vec.corrupt(noise)
            # Unbind object
            v_s = self.get_atom(s).permute(0)
            v_p = self.get_atom(p).permute(1)
            query_key = v_s.bind(v_p)
            unbound = corrupted.bind(query_key).inverse_permute(2)

            sim_true = unbound.cosine_similarity(self.get_atom(o))
            sim_noise = unbound.cosine_similarity(self.get_atom("RandomDummyConcept"))
            results[f"noise_{int(noise*100)}pct"] = {
                "noise_ratio": noise,
                "target_object_similarity": round(sim_true, 4),
                "noise_floor_similarity": round(sim_noise, 4),
                "identified_correctly": sim_true > sim_noise and sim_true > 0.15
            }
        return {
            "tested_triple": f"({s}, {p}, {o})",
            "hyperdimensional_dim": self.dim,
            "resilience_curve": results
        }
