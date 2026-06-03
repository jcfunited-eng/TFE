
"""
rre_cluster_meta.py — Cluster-level wiring of Sentience + Meta-Sentience for RRE

What this gives you:
- A population (cluster) of RRENodes, each wrapped with MetaSentience:
    * self-improvement (alpha/threshold tuning)
    * self-healing via genome snapshots
    * integrity monitoring and runtime regulation
- Simple evolutionary loop:
    * evaluate nodes by average coherence (phi) and energy (E)
    * reproduce via genome crossover + mutation
    * replace weakest with offspring (optional elitism)

Usage:
    from rre_cluster_meta import run_evolution_demo
    results = run_evolution_demo(generations=3, population=4, steps_per_gen=200)
    print(results['fitness_table'])

This module expects rre_sentience.py and rre_meta.py to be in the same directory.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd

from rre_sentience import RRENode, RRECluster, GoalAttractor, synth_signal
from rre_meta import (GenomeManager, MetaController, MetaConfig,
                      IntegrityMonitor, Regulator, MetaSentience)

# ------------------- Support structures -------------------

@dataclass
class WrappedNode:
    node: RRENode
    meta: MetaSentience
    history: List[Dict[str, Any]]

def make_wrapped_node(name: str) -> WrappedNode:
    node = RRENode(name)
    gm = GenomeManager()
    meta = MetaController(MetaConfig(), gm)
    regulator = Regulator()
    integrity = IntegrityMonitor(window=30, z_limit=3.5)
    ms = MetaSentience(node=node, meta=meta, regulator=regulator, integrity=integrity, genome_mgr=gm)
    # initial healthy snapshot
    gm.snapshot(node, comment="initial")
    return WrappedNode(node=node, meta=ms, history=[])

# ------------------- Fitness evaluation -------------------

def evaluate_fitness(records: List[Dict[str, Any]]) -> float:
    """Combine coherence and energy (mean over window)."""
    if not records:
        return -1e9
    phi_vals = [r.get('phi', 0.0) for r in records]
    E_vals   = [r.get('E', 1.0) for r in records]
    return 0.7 * float(np.mean(phi_vals)) + 0.3 * float(np.mean(E_vals) - 1.0)

# ------------------- Evolutionary loop -------------------

def run_evolution_demo(generations: int = 3,
                       population: int = 4,
                       steps_per_gen: int = 200,
                       empathy_weight: float = 0.35,
                       seed_base: int = 100) -> Dict[str, Any]:
    """
    Returns:
        dict with keys: 'fitness_table' (DataFrame), 'population' (list of WrappedNode), 'offspring_count'
    """
    # Build initial wrapped nodes
    wrapped: List[WrappedNode] = [make_wrapped_node(f"N{i+1}") for i in range(population)]
    cluster = RRECluster([w.node for w in wrapped], empathy_weight=empathy_weight)

    # Goals (can be customized)
    goals = [
        GoalAttractor("STABILIZE", target_phi=0.6, risk_aversion=0.7, exploration_bias=0.1),
        GoalAttractor("EXPLORE",   target_phi=0.3, risk_aversion=0.1, exploration_bias=0.8),
        GoalAttractor("GROW",      target_phi=0.9, risk_aversion=0.3, exploration_bias=0.4),
        GoalAttractor("PROTECT",   target_phi=0.5, risk_aversion=0.9, exploration_bias=0.0),
    ]

    fitness_rows = []
    offspring_count = 0

    for gen in range(generations):
        # Fresh signals per node (different regimes to create diversity)
        signals = [synth_signal(n=steps_per_gen+50, seed=seed_base+gen*10+i*7, regime_shifts=4+i%3)
                   for i in range(population)]

        # Run steps
        for t in range(steps_per_gen):
            # Slice windows that grow over time to simulate "experience accumulation"
            windows = [sig.iloc[:50+t] for sig in signals]

            # Cluster-level step (intent selection happens inside)
            _ = cluster.step(windows, goals)

            # Per-node meta step (self-improve, regulate, maybe heal)
            for i, w in enumerate(wrapped):
                info = w.meta.step(windows[i], step_idx=t + gen*steps_per_gen)
                # keep small history record
                rec = dict(phi=info['telemetry'].get('phi', 0.0),
                           E=info['telemetry'].get('E', 1.0),
                           anomaly=info['anomaly'],
                           healed=info['tuning']['healed'])
                w.history.append(rec)

        # Evaluate fitness after generation
        fitness = [evaluate_fitness(w.history[-int(0.5*steps_per_gen):]) for w in wrapped]  # last half-window
        fitness_rows.append({"generation": gen, **{f"N{i+1}": f for i, f in enumerate(fitness)}})

        # Evolve: create one offspring from top-2 and replace worst (elitism=keep best)
        if population >= 3:
            ranked = sorted(list(enumerate(fitness)), key=lambda x: x[1], reverse=True)
            best_idx, second_idx = ranked[0][0], ranked[1][0]
            worst_idx = ranked[-1][0]

            gm = wrapped[best_idx].meta.genome_mgr
            gm2 = wrapped[second_idx].meta.genome_mgr

            # Ensure parents have at least one snapshot; if not, snapshot now
            if not gm.archive: gm.snapshot(wrapped[best_idx].node, "auto-parent-snap")
            if not gm2.archive: gm2.snapshot(wrapped[second_idx].node, "auto-parent-snap")

            child_genome = gm.crossover(gm.archive[-1], gm2.archive[-1], mutation_rate=0.05, seed=gen+seed_base)
            gm.restore(wrapped[worst_idx].node, child_genome)  # overwrite worst with offspring config
            wrapped[worst_idx].history = []  # reset history for fair next-gen eval
            offspring_count += 1

    fitness_df = pd.DataFrame(fitness_rows)
    return {"fitness_table": fitness_df, "population": wrapped, "offspring_count": offspring_count}

if __name__ == "__main__":
    res = run_evolution_demo(generations=2, population=4, steps_per_gen=100)
    print(res["fitness_table"])
    print("Offspring created:", res["offspring_count"])
