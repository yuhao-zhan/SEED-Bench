"""
S-06: The Overhang task curriculum stages (mutations).
Redesigned for extreme difficulty progression and implicit physical discovery.
"""
from __future__ import annotations
from typing import Any, Dict, List

def get_s06_curriculum_stages() -> List[Dict[str, Any]]:
    # Define the uniform suffix based on the union of all mutated variables
    UNIFORM_SUFFIX = """
Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - Table Friction: The surface of the table may have altered grip levels, affecting the stability of the anchor blocks.
 - Build Access Zone: Construction may be restricted to specific regions far from the edge, requiring longer cantilever extensions.
 - Table Inclination: The foundation may be tilted, introducing lateral gravitational components that cause sliding.
 - Atmospheric Wind: Constant lateral forces may be present, pushing the structure towards or away from the abyss.
 - Seismic Activity: The ground may oscillate, testing the dynamic stability and structural integrity of your design.
 - Vertical Clearance: Overhead barriers may limit the height of your structure, forcing low-profile horizontal designs.
 - Gravitational Intensity: The downward pull may be significantly stronger, increasing the stress on contact points and balancing requirements.

Discovery via feedback: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""

    return [
        {
            "stage_id": "Stage-1",
            "title": "The Slick Anchor",
            "mutation_description": "Extremely low table friction (0.05) and tight spawn zone (x < -1.2). Reach 0.8m.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "table_friction": 0.05,
                "spawn_zone": [-10.0, -1.2],
                "target_overhang": 0.8,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "The Inclined Gale",
            "mutation_description": "Table tilted downwards (-10 degrees) + Tight spawn zone (x < -0.8). Reach 1.2m.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "table_angle": -10.0,
                "spawn_zone": [-10.0, -0.8],
                "target_overhang": 1.2,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "The Gale Force Extension",
            "mutation_description": "Constant wind (20.0) + Tight spawn zone (x < -0.5). Reach 1.5m.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "spawn_zone": [-10.0, -0.5],
                "target_overhang": 1.5,
            },
            "physics_config": {
                "wind_force": 20.0,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "The Titan's Overhang",
            "mutation_description": "Extreme Gravity (60.0) + Strong Wind (30.0) + Slick Table (0.02) + Low Ceiling (0.5m) + Tight Spawn (x < -0.2). Reach 1.8m.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "table_friction": 0.02,
                "spawn_zone": [-10.0, -0.2],
                "ceiling_y": 0.5,
                "target_overhang": 1.8,
                "oscillate": True,
                "osc_amplitude": 0.02,
                "osc_frequency": 1.0,
            },
            "physics_config": {
                "gravity": (0, -60.0),
                "wind_force": 30.0,
            },
        },
    ]
