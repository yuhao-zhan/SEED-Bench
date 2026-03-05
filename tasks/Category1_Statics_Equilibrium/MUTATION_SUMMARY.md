# Category 1: Statics & Equilibrium Mutation Summary

This document summarizes the overhauled mutation stages for Category 1 tasks, ensuring high physical reasoning difficulty and "Embodied Discovery" mechanics.

## Task Overview

| Task ID | Base Description | Stage-1 | Stage-2 | Stage-3 | Stage-4 |
|--------|----------------------|---------|---------|---------|---------|
| **S_01** | Bridge: Connect 15m gap for vehicle. | **Anchor Fragility**: Max force 15, torque 50. | **Joint Fragility**: Internal joint torque limit 30. | **Gravity Well**: Gravity -15, Wind -5, Mass 1000kg. | **The Abyss**: Gap 25m, Gravity -20, Mass 1000kg. |
| **S_02** | Skyscraper: Build high on narrow base. | **Brittle Base**: Base joint torque limit 1200. | **Resonance Gale**: Pulsating wind 2500N @ 5Hz. | **Seismic Evolution**: Earthquake evolution 0.1, amp 0.4. | **Gravity Well**: Gravity -25.0. |
| **S_03** | Cantilever: Reach 12m with payload. | **Slalom Tunnel**: Obstacles require winding path. | **Impact Resilience**: Dropped 1000kg load + Gravity -15. | **Weak Foundation**: Non-uniform anchor strengths + Wind. | **Perfect Storm**: Oscillatory wind + 35m reach + Gravity -20. |
| **S_04** | Balancer: Balance 200kg asymmetric load. | **Structural Fragility**: Pivot joint torque limit 8000. | **Aerodynamic Overturning**: Persistent 50N lateral wind. | **The Labyrinth**: Obstacles block standard catch path. | **Kinetic Storm**: Dropped load + Wind + Gravity -20. |
| **S_05** | Shelter: Protect core from meteors. | **Heavier Meteors**: Meteor mass 80kg -> 150kg. | **Reduced Budget**: Structure mass 350kg -> 120kg. | **Gravity + Meteors**: Gravity -60m/s². | **Ultimate Gauntlet**: High gravity + Wind + Fragile Core. |
| **S_06** | Overhang: Stack blocks for max reach. | **Increased Gravity**: Gravity -10 -> -14m/s². | **Reduced Friction**: Friction 0.5 -> 0.08. | **Gravity + Friction**: Gravity -13 + Friction 0.18. | **Titan's Overhang**: Density 0.35 + Gravity -17 + No damping. |

## Detailed Physical Parameters (Overhauled)

### S_01: The Bridge
- **Baseline**: Gap 15m, Gravity -10, Mass 2000kg.
- **Stage-1**: `max_anchor_force: 15.0, max_anchor_torque: 50.0`. Requires distributed anchoring.
- **Stage-2**: `max_joint_torque: 30.0`. Requires robust truss triangulation.
- **Stage-3**: `gravity: -15.0, wind: -5.0, max_structure_mass: 1000.0`. Multi-parameter stress.
- **Stage-4**: `gap_width: 25.0, gravity: -20.0, max_structure_mass: 1000.0`. The ultimate engineering test.

### S_02: The Skyscraper
- **Baseline**: Height > 30m, Width < 12m, Wind 100N, Earthquake 2Hz.
- **Stage-1**: `max_base_torque: 1200.0`. Forces base reinforcement.
- **Stage-2**: `wind_force: 2500.0, wind_frequency: 5.0, wind_oscillatory: True`. High-frequency resonance.
- **Stage-3**: `earthquake_evolution: 0.1, earthquake_amplitude: 0.4`. Chaotic seismic movements.
- **Stage-4**: `gravity: -25.0`. Massive vertical compression.

### S_03: The Cantilever
- **Baseline**: Reach 12m, Load 500kg, Max 2 anchors.
- **Stage-1**: `obstacle_rects: [[5,0,7,6], [10,8,12,20], [15,0,17,4]], target_reach: 25.0`.
- **Stage-2**: `load_type: "dropped", gravity: -15.0, target_reach: 25.0`.
- **Stage-3**: `anchor_strength_map: [...], wind_force: 500.0, gravity: -18.0, target_reach: 28.0`.
- **Stage-4**: `wind_oscillatory: True, target_reach: 35.0, gravity: -20.0`.

### S_04: The Balancer
- **Baseline**: Pivot joint, Gravity -10, Load 200kg.
- **Stage-1**: `fragile_joints: True, max_joint_torque: 8000.0`. Precise static balance.
- **Stage-2**: `wind_active: True, wind_force_multiplier: 50.0`. Asymmetric aerodynamic torque.
- **Stage-3**: `obstacle_active: True, obstacles: [[0.5, 0.0, 2.5, 2.0]]`. Spatial constraints.
- **Stage-4**: `drop_load: True, wind_active: True, gravity: -20.0`. Dynamic impact balance.

## Mutation Patterns

1. **Information Hiding**: Hidden parameters (torque limits, frequencies) are listed in `UNIFORM_SUFFIX` to force embodied discovery.
2. **Essential Difficulty**: Challenges rely on non-linear physics (resonance, structural evolution, fragility) rather than simple scaling.
3. **Cross-Module Consistency**: All thresholds are synchronized across `environment.py`, `evaluator.py`, `feedback.py`, and `prompt.py`.
