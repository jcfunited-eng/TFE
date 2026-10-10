# Formal Architecture Specification: 4-Column 3D Modular Neuromorphic Substrate (GualaLoom Core)
**Document ID**: DSF-GUALA-SPEC-2026-V5  
**Classification**: Proprietary Trade Secret / Commercial & DARPA Technical Specification  
**Authority**: Senior DARPA Neuromorphic Systems Architect  
**Substrate**: ArcLoom Discrete Ternary Neuromorphic Fabric (Non-Von Neumann, Asynchronous, Balanced-Ternary)  
**Dimensional Authority**: DSF-AI Kernel ($L_0 - L_4$)  

---

## 1. Executive Summary & Hardware Boundary

This document establishes the formal physical, mathematical, and structural specification for transitioning the **GualaLoom cognitive substrate** from a single flat 2D associative crossbar ($1,024 \times 1,024$) to a **4-Column 3D Modular Neuromorphic Substrate** with vertical laminar microcircuit depth.

### 1.1 Hardware Boundary & Invariance Laws
1. **Zero Disembodied Chatbot Persona**: Guala is an embodied autonomous physical system governed strictly by causal sensorimotor physics, contact mechanics, and energetic conservation.
2. **Zero Statistical ML / Backpropagation**: Weight adaptation is governed locally by continuum material yield stress plasticity ($f = |\sigma| - Y \le 0$) at physical contact bridges, operating without global loss gradients, backpropagation, or floating-point matrix multipliers.
3. **Hardware Deployment Roadmap**:
   - **Phase A (Current)**: High-performance software-emulated ternary substrate in native Rust (`native/guala_core/`) interfacing with the live embodied world.
   - **Phase B (DARPA Tactical Demo)**: Edge hardware co-processing demonstration on the PYNQ-Z2 (Zynq-7020) for spatial sensorimotor reflexes, while the deep laminar 3D modular columns execute in the compiled Rust engine.
   - **Phase C (Silicon Tape-Out)**: Full custom balanced-ternary ASIC implementing physical 3D vertical through-silicon via (TSV) columnar interconnects.

---

## 2. The 4 Modular Cortical Columns

Rather than packing all modalities into a single flat associative sheet, the substrate factors physical reality into four orthogonal, specialized cortical columns:

```
+---------------------------------------------------------------------------------------------------+
|                                  4-COLUMN 3D MODULAR SUBSTRATE                                    |
+---------------------------------------------------------------------------------------------------+
|      COLUMN 0      |             COLUMN 1             |          COLUMN 2          |   COLUMN 3   |
|     MULTIMODAL     |       SPATIAL & TOPOLOGICAL      |       CAUSAL SYNTAX        |   MATERIAL   |
|    TRANSDUCTION    |             INVARIANCE           |       & COMBINATORIAL      |  AFFORDANCE  |
|                    |                                  |          CHAINING          |  & BARRIERS  |
+--------------------+----------------------------------+----------------------------+--------------+
| • Optical Retina   | • Polar Coordinates (r, θ)       | • Asymmetric Delay Fasciculi| • Yield Y   |
| • Cochlear ERB     | • Object Permanence Attractor    | • 3-5 Step Temporal Syntax | • Rigid Stop |
| • Tactile Skin     | • Occlusion Blindout Resistance  | • Demand Proto-Phrasing    | • Compliance |
+--------------------+----------------------------------+----------------------------+--------------+
          ▲                           ▲                               ▲                      ▲
          └───────────────────────────┴───────────────┬───────────────┴──────────────────────┘
                                                      ▼
                                       [INTER-COLUMN DIRECTIONAL FASCICULI]
                                     von Mises Plasticity: f = ||σ_ij|| - Y <= 0
```

### Column Specifications:

1. **Column 0: Multimodal Sensory Transduction**:
   - Transduces continuous sensory streams into wide discrete ternary strands: $\mathbf{T}^{\text{sensory}} \in \{-1, 0, +1\}^{512}$.
   - Sub-channels: 19,200 optical ray visual field, 16-channel cochlear ERB filterbank, tactile roughness/compliance/temperature ($mK$), and gustatory tastants.

2. **Column 1: Spatial & Topological Invariance**:
   - Encodes egocentric polar space ($r, \theta$) and room topology.
   - **Object Permanence Attractor**: Maintains a circulating topological attractor state when an object passes behind obstacles or leaves active retinal gaze. The coordinate manifold does not collapse during sensor blindout.

3. **Column 2: Causal Sequential Syntax & Combinatorial Chaining**:
   - Governed by **asymmetric directional plastic delay fasciculi** ($G_{ij} \neq G_{ji}$).
   - Encodes temporal succession: $A \xrightarrow{\tau_1} B \xrightarrow{\tau_2} C$.
   - Drives multi-step motor execution and combinatorial vocal phonemic chaining (`[syl1, syl2, syl3]`).

4. **Column 3: Material Affordance & Barrier Gating**:
   - Enforces physical conservation boundaries. Evaluates contact stress $\sigma$ against material yield limit $Y$.
   - Produces immediate, sub-microsecond refusal pulses on rigid barriers (walls, furniture), eliminating trial-and-error physical collisions.

---

## 3. The 3D Laminar Microcircuit (Vertical Depth)

Each of the 4 columns contains an identical **6-layer vertical laminar microcircuit**, eliminating flat-matrix cross-talk and enabling predictive feedback:

```
                      ▲
                      │ Top-down Neuromodulation
   ┌──────────────────┴──────────────────────────────────────┐
   │ LAYER 1: Apical Dendrite Field                         │
   │ Global state, circadian gating, somatic arousal         │
   └──────────────────┬──────────────────────────────────────┘
                      │
   ┌──────────────────▼──────────────────────────────────────┐
   │ LAYERS 2/3: Supragranular Associative Lattice           │
   │ • Dense recurrent ternary crossbar {-1, 0, +1}          │
   │ • Horizontal lateral inhibition (Sparsity: 2% - 5%)     │
   │ • Inter-column corticocortical projections              │
   └─────────────┬─────────────────────────────▲─────────────┘
                 │                             │
   ┌─────────────▼─────────────┐ ┌─────────────┴─────────────┐
   │ LAYER 4: Granular Input   │ │ LAYER 6: Predictive Feedback│
   │ Direct sensory afferents  │ │ Reafference cancellation, │
   │ Trits from lower stream   │ │ corticothalamic tuning    │
   └───────────────────────────┘ └───────────────────────────┘
                 │
   ┌─────────────▼───────────────────────────────────────────┐
   │ LAYER 5: Infragranular Motor Pyramidal Efferents        │
   │ • Continuous potential venting (P_k > B_k)              │
   │ • Motor kinematic strides & articulatory vocal drive    │
   │ • Efference copy to Layer 6                             │
   └─────────────────────────────────────────────────────────┘
                      │
                      ▼ Motor / Acoustic Actuation
```

### 3.1 Causal Dynamic Flow Inside a Column
1. **Afferent Influx (L4)**: Sensory input arrives at Layer 4.
2. **Associative Integration (L2/3)**: L4 excites Layer 2/3, where recurrent horizontal connections settle into an invariant attractor motif. Lateral inhibitory trits enforce high sparsity ($>95\%$ quiescent).
3. **Motor Emission (L5)**: When L2/3 resonance exceeds threshold and somatic pressure indicates action ($P_k > B_k$), Layer 5 triggers motor or vocal actuation.
4. **Efference Copy & Predictive Cancellation (L5 $\rightarrow$ L6 $\rightarrow$ L4)**: Layer 5 immediately transmits a copy of the emitted command to Layer 6, which projects inhibitory signals back to Layer 4 to cancel self-generated sensory reafference.

---

## 4. Mathematical Formulation of 3D Plasticity

### 4.1 Node States & Conductance Tensors
Each column $c \in \{0, 1, 2, 3\}$ has $L = 6$ laminar layers, with $N_l$ discrete ternary nodes per layer:
$$T_{c, l, i} \in \{-1, 0, +1\}, \quad i \in \{1, \dots, N_l\}$$

### 4.2 Intra-Column Laminar Conductance Tensor
Within a column, connections exist between defined laminar pairs $(l, l')$:
$$\mathbf{G}_{c}^{(l, l')} \in [-1.0, 1.0]^{N_l \times N_{l'}}$$

### 4.3 Inter-Column Fasciculi Conductance Tensor
Long-range white-matter tracts connect Layer 2/3 and Layer 5 between distinct columns $c$ and $c'$:
$$\mathbf{W}_{(c, c')} \in [-1.0, 1.0]^{N_{2/3} \times N_{2/3}}$$

### 4.4 Continuum Yield Stress Plasticity
Plastic flow across any connection bridge $g_{ij}$ occurs if and only if localized tensor stress exceeds the yield threshold $Y$:
$$f(\sigma_{ij}) = |\sigma_{ij}| - Y \le 0$$
$$\sigma_{ij}(t) = T_i(t) \cdot T_j(t) - g_{ij}(t)$$
$$\dot{\lambda} \ge 0, \quad \dot{\lambda} \cdot f(\sigma_{ij}) = 0$$
$$\Delta g_{ij} = \eta \cdot \dot{\lambda} \cdot \text{sgn}(\sigma_{ij})$$
Where $Y \in [0.4, 0.8]$ is the material yield limit and $\eta \in [0.01, 0.05]$ is the plastic hardening rate.

### 4.5 Synaptic Downscaling & Dream Consolidation (Offline Sleep)
During the offline sleep cycle ($M_k \approx 0$), all conductances undergo global synaptic downscaling to enforce energetic bounds and eliminate spurious weak connections:
$$g_{ij}(t + 1) = \begin{cases}
g_{ij}(t) \cdot (1 - \gamma_{\text{decay}}), & \text{if } |g_{ij}(t)| \ge \theta_{\text{prune}} \\
0.0, & \text{if } |g_{ij}(t)| < \theta_{\text{prune}}
\end{cases}$$

---

## 5. Technical Delivery & Verification Milestones

### Milestone 1: Native Rust Core Implementation (`native/guala_core/`)
- Implement `cortical_column.rs` defining `LaminarMicrocircuit`, `CorticalColumn`, and `ModularSubstrate4D`.
- Expose zero-copy PyO3 bindings in `lib.rs`.
- Compile and verify release wheel: `guala_core-0.1.0-cp311-cp311-manylinux_2_35_x86_64.whl`.
- Unit test suite: Verify $0.00\%$ bit error rate under cross-talk and verify efference copy self-cancellation.

### Milestone 2: Functional Organism Integration (`dsf_ai_service/`)
- Wire `ModularSubstrate4D` into `dsf_ai_service/guala_functional_organism.py`.
- Couple Column 1 to egocentric polar tracking.
- Couple Column 2 to 3-step combinatorial syntax chaining.

### Milestone 3: Live Verification & Telemetry Receipts
- Execute zero-drain cutover on ECS.
- Record live multi-beat vocal phrases (`syl1 -> syl2 -> syl3`) and spatial occlusion permanence receipts.
