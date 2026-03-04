"""
S-02: The Skyscraper task curriculum stages (mutations).
"""

from __future__ import annotations

from typing import Any, Dict, List

UNIFORM_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - Structural Integrity Limit: Connections between beams now have a finite breaking strength. Excessive stress from weight or movement will cause joints to snap.
 - Wind Shear Profile: Lateral wind forces may increase non-linearly with height, creating extreme pressure on the upper structure.
 - Seismic Oscillation Rate: The rate of ground vibration may vary, potentially inducing destructive resonance in specific designs.
 - Ground Displacement Intensity: The base movement magnitude may be significantly higher, testing the flexibility of the foundation.
 - Seismic Intensity Evolution: The earthquake's power may grow over time, requiring long-term structural resilience.
 - Wind Pulsation: Wind forces may fluctuate periodically, creating dynamic loading patterns that test structural damping.
 - Gravitational Intensity: The downward pull may be stronger, increasing the load on all structural members and joints.

Discovery via feedback: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""

def get_s02_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for S-02: The Skyscraper task variants.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Structural Integrity Threshold",
            "mutation_description": "Joints now have a finite breaking strength. Heavy, rigid towers will snap their base connections during seismic activity.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "earthquake_amplitude": 1.0,
            },
            "physics_config": {
                "max_joint_force": 1000000.0,
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Extreme High-Altitude Shear",
            "mutation_description": "Wind force increases dramatically with height. Tall structures must account for non-linear lateral pressure.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "wind_force": 300.0,
                "wind_shear_factor": 1.2,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Resonant Fragility",
            "mutation_description": "Combined high-frequency earthquake and limited joint strength. Resonance will quickly exceed structural limits.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "earthquake_frequency": 6.0,
                "earthquake_amplitude": 0.8,
            },
            "physics_config": {
                "max_joint_force": 2000000.0,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "The Harmonic Vortex",
            "mutation_description": "Evolving earthquake intensity combined with oscillating winds and fragile joints. The ultimate test of dynamic stability.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "earthquake_amplitude": 0.5,
                "earthquake_frequency": 5.0,
                "earthquake_amplitude_evolution": 0.08,
                "wind_force": 350.0,
                "wind_oscillation_frequency": 2.0,
            },
            "physics_config": {
                "max_joint_force": 5000000.0,
                "gravity": (0, -12.0),
            },
        },
    ]
