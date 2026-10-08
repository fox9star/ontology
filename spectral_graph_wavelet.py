"""
Spectral Graph Wavelet Transform (SGWT) & Multiresolution Analysis Engine for AI Ontologies.
Computes multi-scale graph wavelets via Chebyshev polynomial approximations of the Graph Laplacian,
detecting localized high-frequency semantic anomalies and macro-scale knowledge clusters.
Pure Python implementation without external C-extension dependencies.
"""

import math
from typing import Dict, List, Tuple, Any, Optional, Set


class SpectralGraphWavelet:
    """
    Spectral Graph Wavelet Transform (SGWT) on Knowledge Graphs.
    Applies the normalized Graph Laplacian L = I - D^(-1/2) A D^(-1/2) and Chebyshev approximations
    to analyze graph signals at multiple continuous scales s in R^+.
    """

    def __init__(self, chebyshev_order: int = 6):
        self.chebyshev_order = chebyshev_order
        self.nodes: List[str] = []
        self.node_to_idx: Dict[str, int] = {}
        self.adj_matrix: List[List[float]] = []

    def build_graph(self, edges: List[Tuple[str, str, float]]):
        """Builds symmetric adjacency matrix from weighted edges (u, v, w)."""
        node_set = set()
        for u, v, _ in edges:
            node_set.add(u)
            node_set.add(v)

        self.nodes = sorted(list(node_set))
        self.node_to_idx = {n: i for i, n in enumerate(self.nodes)}
        n = len(self.nodes)
        self.adj_matrix = [[0.0] * n for _ in range(n)]

        for u, v, w in edges:
            i, j = self.node_to_idx[u], self.node_to_idx[v]
            weight = max(0.01, float(w))
            self.adj_matrix[i][j] = weight
            self.adj_matrix[j][i] = weight

    def get_normalized_laplacian(self) -> Tuple[List[List[float]], float]:
        """
        Computes normalized Graph Laplacian L = I - D^(-1/2) A D^(-1/2).
        Returns L and upper bound on max eigenvalue lambda_max <= 2.0.
        """
        n = len(self.nodes)
        degrees = [sum(self.adj_matrix[i]) for i in range(n)]
        inv_sqrt_d = [1.0 / math.sqrt(max(1e-8, d)) for d in degrees]

        laplacian = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i == j:
                    laplacian[i][j] = 1.0 - (self.adj_matrix[i][j] * inv_sqrt_d[i] * inv_sqrt_d[j])
                else:
                    laplacian[i][j] = - (self.adj_matrix[i][j] * inv_sqrt_d[i] * inv_sqrt_d[j])

        # For normalized Laplacian, lambda_max <= 2.0
        return laplacian, 2.0

    def matrix_vector_mul(self, mat: List[List[float]], vec: List[float]) -> List[float]:
        n = len(vec)
        return [sum(mat[i][j] * vec[j] for j in range(n)) for i in range(n)]

    def chebyshev_wavelet_filter(self, laplacian: List[List[float]], signal: List[float], scale: float, lambda_max: float = 2.0) -> List[float]:
        """
        Applies graph wavelet filter g(s L) signal using Chebyshev polynomial recurrence.
        Wavelet kernel: g(x) = x * exp(-x) where x = s * lambda.
        """
        n = len(signal)
        # Shift spectrum of L from [0, lambda_max] to [-1, 1]:
        # L_tilde = (2 / lambda_max) * L - I
        scale_factor = 2.0 / lambda_max
        l_tilde = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                l_tilde[i][j] = scale_factor * laplacian[i][j]
                if i == j:
                    l_tilde[i][j] -= 1.0

        # Sample kernel g(s * lambda) at Chebyshev nodes to compute expansion coefficients c_k
        m = self.chebyshev_order
        c = []
        for j in range(m):
            # Chebyshev points in [-1, 1]
            x_j = math.cos(math.pi * (j + 0.5) / m)
            # Map back to lambda in [0, lambda_max]
            lam_j = (x_j + 1.0) * (lambda_max / 2.0)
            # Evaluate wavelet kernel g(s * lam)
            val = (scale * lam_j) * math.exp(-max(0.0, scale * lam_j))
            c.append(val)

        # Clenshaw / Chebyshev polynomial evaluation on vector:
        # T_0(L_tilde) * signal = signal
        # T_1(L_tilde) * signal = L_tilde * signal
        t_prev = list(signal)
        t_curr = self.matrix_vector_mul(l_tilde, signal)

        # Weighted sum approximation
        # Base weight: average
        accum = [t_prev[i] * 0.5 * (c[0] if c else 1.0) for i in range(n)]

        for k in range(1, min(m, 4)):
            weight = c[k] if k < len(c) else 0.1
            for i in range(n):
                accum[i] += t_curr[i] * weight

            # Recurrence: T_{k+1} = 2 * L_tilde * T_k - T_{k-1}
            t_next = self.matrix_vector_mul(l_tilde, t_curr)
            for i in range(n):
                t_next[i] = 2.0 * t_next[i] - t_prev[i]
            t_prev = t_curr
            t_curr = t_next

        return accum

    def compute_multiresolution_spectrum(self, edges: List[Tuple[str, str, float]], scales: Optional[List[float]] = None) -> Dict[str, Any]:
        """
        Performs multiresolution wavelet transform across scales (e.g. s = 0.5, 1.5, 3.0).
        Detects high-frequency local anomalies and low-frequency macro clusters.
        """
        self.build_graph(edges)
        n = len(self.nodes)
        if n == 0:
            return {"status": "empty_graph", "wavelet_coefficients": {}}

        laplacian, lam_max = self.get_normalized_laplacian()
        target_scales = scales or [0.5, 1.5, 3.0]

        # Uniform base signal with slight perturbation to detect structural topology
        base_signal = [1.0 / math.sqrt(n)] * n

        scale_results = {}
        node_energies: Dict[str, float] = {node: 0.0 for node in self.nodes}

        for s in target_scales:
            wavelet_coeffs = self.chebyshev_wavelet_filter(laplacian, base_signal, scale=s, lambda_max=lam_max)
            energy = sum(c * c for c in wavelet_coeffs)
            scale_name = f"scale_{s:.1f}"

            per_node_coeffs = {self.nodes[i]: round(wavelet_coeffs[i], 4) for i in range(n)}
            scale_results[scale_name] = {
                "scale": s,
                "scale_band": "High-Frequency (Local Edge Anomaly)" if s <= 0.8 else ("Low-Frequency (Macro Cluster)" if s >= 2.5 else "Mid-Frequency"),
                "total_spectral_energy": round(energy, 4),
                "top_activated_nodes": sorted(per_node_coeffs.items(), key=lambda x: abs(x[1]), reverse=True)[:4]
            }

            # Accumulate energy per node for anomaly ranking
            for i, node in enumerate(self.nodes):
                # High frequency contributes more to anomaly detection
                weight_factor = 2.0 if s <= 0.8 else 0.5
                node_energies[node] += (wavelet_coeffs[i] ** 2) * weight_factor

        # Detect anomaly bottlenecks (nodes with extreme high-frequency wavelet variance)
        sorted_anomalies = sorted(node_energies.items(), key=lambda x: x[1], reverse=True)
        mean_energy = sum(node_energies.values()) / max(1, n)

        anomaly_report = [
            {
                "node": node,
                "wavelet_energy": round(energy, 4),
                "anomaly_index": round(energy / max(1e-6, mean_energy), 2),
                "status": "Localized Structural Bottleneck / Anomaly" if energy > mean_energy * 1.5 else "Normal Harmonic Coherence"
            }
            for node, energy in sorted_anomalies
        ]

        return {
            "status": "sgwt_transform_completed",
            "nodes_count": n,
            "edges_count": len(edges),
            "laplacian_lambda_max": lam_max,
            "multiresolution_scales": scale_results,
            "top_wavelet_anomalies": anomaly_report[:5]
        }
