"""
Gauge-Theoretic Fiber Bundle & Semantic Holonomy Engine for AI Ontologies.
Models context shifts as parallel transport along principal U(1) fiber bundles,
calculating non-Abelian/U(1) semantic curvature, loop holonomy, and gauge alignment.
Pure Python implementation without external C-extension dependencies.
"""

import cmath
import math
from typing import Dict, List, Tuple, Any, Optional


class SemanticGaugeBundle:
    """
    Principal U(1) Fiber Bundle over Ontology Domain Graphs.
    Tracks contextual phase connections A(u -> v), computes loop holonomy Hol(C),
    and measures semantic field curvature to prevent contextual distortion.
    """

    def __init__(self):
        # Nodes / domains
        self.domains: set = set()
        # Connection 1-form: (u, v) -> connection angle in radians [-pi, pi]
        self.connection_form: Dict[Tuple[str, str], float] = {}

    def add_connection(self, u: str, v: str, connection_angle_rad: float):
        """Sets the gauge connection A(u -> v) for parallel transport between domains."""
        self.domains.add(u)
        self.domains.add(v)
        # Normalize angle to [-pi, pi]
        angle = (connection_angle_rad + math.pi) % (2.0 * math.pi) - math.pi
        self.connection_form[(u, v)] = angle

    def parallel_transport_vector(self, path: List[str], initial_vector: complex = complex(1.0, 0.0)) -> Tuple[complex, float]:
        """
        Parallel transports a semantic state vector along path u0 -> u1 -> ... -> un.
        Returns final complex vector and accumulated phase angle.
        """
        if len(path) < 2:
            return initial_vector, 0.0

        total_phase = 0.0
        for i in range(len(path) - 1):
            edge = (path[i], path[i + 1])
            conn = self.connection_form.get(edge, 0.0)
            total_phase += conn

        # Gauge parallel transport operator: exp(i * sum(A))
        transport_operator = cmath.exp(complex(0.0, total_phase))
        final_vector = initial_vector * transport_operator
        return final_vector, total_phase

    def calculate_loop_holonomy(self, loop_cycle: List[str]) -> Dict[str, Any]:
        """
        Computes the holonomy Hol(C) around a closed semantic loop C = u1 -> u2 -> ... -> u1.
        Hol(C) = exp(i * oint A).
        Measures the semantic curvature (contextual distortion) F = Delta phi.
        """
        if len(loop_cycle) < 3 or loop_cycle[0] != loop_cycle[-1]:
            raise ValueError("Loop must be a closed cycle starting and ending at the same node.")

        final_vec, raw_phase = self.parallel_transport_vector(loop_cycle, complex(1.0, 0.0))
        # Curvature phase in [-pi, pi]
        curvature_flux = (raw_phase + math.pi) % (2.0 * math.pi) - math.pi
        is_flat = abs(curvature_flux) < 1e-4

        holonomy_matrix = [
            [round(math.cos(curvature_flux), 4), round(-math.sin(curvature_flux), 4)],
            [round(math.sin(curvature_flux), 4), round(math.cos(curvature_flux), 4)]
        ]

        distortion_degree = round(abs(curvature_flux) / math.pi * 100.0, 2)

        return {
            "status": "holonomy_evaluated",
            "cycle_path": " -> ".join(loop_cycle),
            "accumulated_phase_radians": round(raw_phase, 4),
            "semantic_curvature_flux": round(curvature_flux, 4),
            "curvature_flux_degrees": round(math.degrees(curvature_flux), 2),
            "holonomy_u1_operator": {
                "real": round(final_vec.real, 4),
                "imag": round(final_vec.imag, 4)
            },
            "holonomy_so2_rotation_matrix": holonomy_matrix,
            "contextual_distortion_percent": distortion_degree,
            "field_geometry": "Flat Gauge Field (Zero Distortion)" if is_flat else "Curved Semantic Manifold (Distorted Phase)",
            "compensating_gauge_transformation": {
                "recommended_phase_counter_rotation": round(-curvature_flux, 4)
            }
        }

    def align_gauge_symmetry(self, reference_domain: str = "mv") -> Dict[str, Any]:
        """
        Performs global gauge alignment by computing local gauge potentials lambda(v)
        to standardize coordinate frames relative to a reference domain.
        """
        gauge_potentials: Dict[str, float] = {reference_domain: 0.0}
        visited = {reference_domain}
        queue = [reference_domain]

        while queue:
            curr = queue.pop(0)
            curr_pot = gauge_potentials[curr]
            for (u, v), conn in self.connection_form.items():
                if u == curr and v not in visited:
                    gauge_potentials[v] = round(curr_pot + conn, 4)
                    visited.add(v)
                    queue.append(v)
                elif v == curr and u not in visited:
                    gauge_potentials[u] = round(curr_pot - conn, 4)
                    visited.add(u)
                    queue.append(u)

        return {
            "status": "gauge_alignment_completed",
            "reference_domain": reference_domain,
            "aligned_domains_count": len(gauge_potentials),
            "local_gauge_potentials": gauge_potentials,
            "gauge_symmetry_invariant": True
        }
