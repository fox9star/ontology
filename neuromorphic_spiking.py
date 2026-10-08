"""
Neuromorphic Spiking Neural Knowledge Graph Engine with STDP Plasticity.
Implements Leaky Integrate-and-Fire (LIF) continuous dynamics and
Spike-Timing-Dependent Plasticity (STDP) for temporal causal reinforcement of ontology relations.
Pure Python implementation without external C-extension dependencies.
"""

import math
import random
from typing import Dict, List, Tuple, Any, Optional


class LIFNeuron:
    """Leaky Integrate-and-Fire (LIF) biological spiking neuron."""
    __slots__ = ('name', 'v', 'v_rest', 'v_reset', 'v_th', 'tau_m', 'refractory_time', 'last_spike_time')

    def __init__(self, name: str, v_rest: float = -70.0, v_reset: float = -75.0, v_th: float = -50.0, tau_m: float = 10.0):
        self.name = name
        self.v_rest = v_rest
        self.v_reset = v_reset
        self.v_th = v_th
        self.tau_m = tau_m
        self.v = v_rest
        self.refractory_time = 0.0
        self.last_spike_time = -999.0

    def step(self, dt: float, current_in: float, current_time: float) -> bool:
        """
        Integrates membrane voltage over dt (ms).
        Returns True if an action potential spike is fired.
        """
        if self.refractory_time > 0.0:
            self.refractory_time = max(0.0, self.refractory_time - dt)
            self.v = self.v_reset
            return False

        # dV/dt = -(V - V_rest)/tau_m + I_in
        dv = (-(self.v - self.v_rest) / self.tau_m + current_in) * dt
        self.v += dv

        if self.v >= self.v_th:
            self.v = self.v_reset
            self.refractory_time = 2.0  # 2 ms absolute refractory period
            self.last_spike_time = current_time
            return True
        return False


class NeuromorphicSpikingKG:
    """
    Neuromorphic Knowledge Graph Network.
    Maps ontology entities to spiking neurons and ontology relations to plastic synapses.
    Dynamically reinforces causal associations via STDP.
    """

    def __init__(self):
        self.neurons: Dict[str, LIFNeuron] = {}
        # Synapses: (pre, post) -> weight in [0.01, 1.0]
        self.synapses: Dict[Tuple[str, str], float] = {}
        self.spike_history: List[Dict[str, Any]] = []

    def add_entity(self, name: str):
        if name not in self.neurons:
            self.neurons[name] = LIFNeuron(name)

    def add_relation_synapse(self, pre: str, post: str, initial_weight: float = 0.3):
        self.add_entity(pre)
        self.add_entity(post)
        self.synapses[(pre, post)] = max(0.01, min(1.0, float(initial_weight)))

    def apply_stdp(self, pre: str, post: str, t_pre: float, t_post: float, A_plus: float = 0.06, A_minus: float = 0.05, tau: float = 15.0):
        """
        Spike-Timing-Dependent Plasticity rule.
        dt = t_post - t_pre.
        dt > 0: Pre fires before post -> Causal Long-Term Potentiation (LTP).
        dt < 0: Post fires before pre -> Anti-causal Long-Term Depression (LTD).
        """
        delta_t = t_post - t_pre
        if (pre, post) not in self.synapses:
            return

        w_old = self.synapses[(pre, post)]
        if delta_t > 0:
            # LTP
            dw = A_plus * math.exp(-delta_t / tau)
        elif delta_t < 0:
            # LTD
            dw = -A_minus * math.exp(delta_t / tau)
        else:
            dw = 0.0

        w_new = max(0.01, min(1.0, w_old + dw))
        self.synapses[(pre, post)] = round(w_new, 4)

    def simulate(self, duration_ms: float = 100.0, dt: float = 0.5, external_stimuli: Optional[Dict[str, List[float]]] = None) -> Dict[str, Any]:
        """
        Runs continuous-time spiking simulation with synaptic currents and STDP.
        external_stimuli: {entity_name: [spike_times_ms...]}
        """
        stimuli = external_stimuli or {}
        steps = int(duration_ms / dt)
        raster: Dict[str, List[float]] = {n: [] for n in self.neurons}
        initial_weights = dict(self.synapses)

        for step_i in range(steps):
            t = step_i * dt

            # 1. Compute input currents for each neuron
            currents = {n: 0.0 for n in self.neurons}

            # External stimulus injection
            for entity, times in stimuli.items():
                if entity in currents:
                    for stim_t in times:
                        if abs(t - stim_t) < (dt * 0.9):
                            currents[entity] += 60.0  # Supra-threshold current pulse

            # Synaptic transmission from recently spiked pre-synaptic neurons
            for (pre, post), w in self.synapses.items():
                pre_neuron = self.neurons[pre]
                time_since_pre_spike = t - pre_neuron.last_spike_time
                if 0.0 < time_since_pre_spike < 15.0:
                    # Exponential synaptic conductance decay
                    syn_current = w * 45.0 * math.exp(-time_since_pre_spike / 4.0)
                    currents[post] += syn_current

            # 2. Update all LIF neurons
            spiked_now = []
            for name, neuron in self.neurons.items():
                has_spiked = neuron.step(dt, currents[name], t)
                if has_spiked:
                    spiked_now.append(name)
                    raster[name].append(round(t, 2))

            # 3. Apply STDP to active synapses
            for post in spiked_now:
                # Check all incoming pre-synaptic connections
                for (pre, tgt), w in self.synapses.items():
                    if tgt == post:
                        t_pre = self.neurons[pre].last_spike_time
                        if t_pre > 0.0 and (t - t_pre) < 40.0:
                            self.apply_stdp(pre, post, t_pre, t)

            for pre in spiked_now:
                # Check outgoing post-synaptic connections (LTD check)
                for (src, post), w in self.synapses.items():
                    if src == pre:
                        t_post = self.neurons[post].last_spike_time
                        if t_post > 0.0 and (t - t_post) < 40.0:
                            self.apply_stdp(pre, post, t, t_post)

        # Calculate statistics
        firing_rates = {n: round(len(spikes) / (duration_ms / 1000.0), 1) for n, spikes in raster.items()}
        weight_changes = []
        for (pre, post), w_new in self.synapses.items():
            w_old = initial_weights.get((pre, post), 0.3)
            weight_changes.append({
                "synapse": f"{pre} -> {post}",
                "initial_weight": round(w_old, 3),
                "adapted_weight": round(w_new, 3),
                "change_percent": round(((w_new - w_old) / max(1e-4, w_old)) * 100, 1),
                "causal_potentiation": w_new > w_old
            })

        return {
            "status": "neuromorphic_simulation_completed",
            "duration_ms": duration_ms,
            "neuron_count": len(self.neurons),
            "synapse_count": len(self.synapses),
            "firing_rates_hz": firing_rates,
            "raster_plot_summary": {k: v[:6] for k, v in raster.items() if v},
            "synaptic_plasticity_changes": weight_changes
        }
