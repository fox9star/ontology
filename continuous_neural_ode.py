"""
Continuous-Time Neural Ordinary Differential Equations (Neural ODE) Engine for AI Ontologies.
Models the continuous temporal flow of ontology latent states using Runge-Kutta 4th Order (RK4)
numerical integration, phase portrait analysis, and dynamical attractor stability diagnostics.
Pure Python implementation without external C-extension dependencies.
"""

import math
from typing import Dict, List, Tuple, Any, Optional, Callable


class ContinuousNeuralODE:
    """
    Continuous Neural ODE Dynamical System.
    Solves dz(t)/dt = f_theta(z, t) across continuous time t in R^+ using explicit RK4 integration.
    """

    def __init__(self, sigma: float = 10.0, rho: float = 28.0, beta: float = 8.0 / 3.0):
        # Dynamical coupling coefficients (Lorenz/Semantic attractor parameters)
        self.sigma = sigma
        self.rho = rho
        self.beta = beta

    def vector_field(self, z: List[float], t: float, control_input: float = 0.0) -> List[float]:
        """
        Computes velocity dz/dt = [dz1/dt, dz2/dt, dz3/dt].
        z1: Cognitive momentum / agent activity
        z2: Semantic complexity / entropy
        z3: Ontological coherence / consistency
        """
        z1, z2, z3 = z[0], z[1], z[2]
        dz1 = self.sigma * (z2 - z1) + control_input
        dz2 = z1 * (self.rho - z3) - z2
        dz3 = z1 * z2 - self.beta * z3
        return [dz1, dz2, dz3]

    def rk4_step(self, z: List[float], t: float, h: float, control_input: float = 0.0) -> List[float]:
        """Explicit Runge-Kutta 4th-Order numerical integration step."""
        k1 = self.vector_field(z, t, control_input)

        z_k2 = [zi + 0.5 * h * ki for zi, ki in zip(z, k1)]
        k2 = self.vector_field(z_k2, t + 0.5 * h, control_input)

        z_k3 = [zi + 0.5 * h * ki for zi, ki in zip(z, k2)]
        k3 = self.vector_field(z_k3, t + 0.5 * h, control_input)

        z_k4 = [zi + h * ki for zi, ki in zip(z, k3)]
        k4 = self.vector_field(z_k4, t + h, control_input)

        z_next = [
            zi + (h / 6.0) * (k1i + 2.0 * k2i + 2.0 * k3i + k4i)
            for zi, k1i, k2i, k3i, k4i in zip(z, k1, k2, k3, k4)
        ]
        return z_next

    def integrate_trajectory(self, z0: List[float], t_span: Tuple[float, float] = (0.0, 5.0), dt: float = 0.05, control_input: float = 0.0) -> Dict[str, Any]:
        """
        Integrates continuous trajectory over t_span [t0, t1].
        Returns timestamped states, velocities, and phase portrait metrics.
        """
        t0, t1 = t_span
        steps = int(max(1, (t1 - t0) / dt))

        times = []
        states = []
        velocities = []
        current_z = list(z0)
        current_t = t0

        for _ in range(steps + 1):
            times.append(round(current_t, 3))
            states.append([round(v, 4) for v in current_z])
            vel = self.vector_field(current_z, current_t, control_input)
            velocities.append([round(v, 4) for v in vel])

            current_z = self.rk4_step(current_z, current_t, dt, control_input)
            current_t += dt

        # Compute phase portrait diagnostics
        # Divergence div(F) = df1/dz1 + df2/dz2 + df3/dz3 = -sigma - 1 - beta
        divergence = -self.sigma - 1.0 - self.beta
        is_dissipative = divergence < 0.0

        # Trajectory energy / norm
        norms = [math.sqrt(sum(v * v for v in state)) for state in states]
        avg_energy = sum(norms) / len(norms)
        max_energy = max(norms)

        return {
            "status": "trajectory_integrated_successfully",
            "initial_state": z0,
            "final_state": states[-1],
            "time_span": [t0, t1],
            "step_count": len(times),
            "step_size_dt": dt,
            "system_divergence": round(divergence, 4),
            "phase_space_contraction": is_dissipative,
            "attractor_type": "Strange Chaotic Attractor" if abs(self.rho - 28.0) < 1.0 else "Stable Fixed Point",
            "average_trajectory_norm": round(avg_energy, 4),
            "peak_trajectory_norm": round(max_energy, 4),
            "trajectory_samples": [
                {"t": times[i], "z": states[i], "dz_dt": velocities[i]}
                for i in range(0, len(times), max(1, len(times) // 10))
            ]
        }
