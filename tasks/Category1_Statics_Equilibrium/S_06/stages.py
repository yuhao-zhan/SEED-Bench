"""
S-06: The Overhang task curriculum stages (mutations).
Redesigned for extreme difficulty progression and implicit physical discovery.
"""
from __future__ import annotations
from typing import Any, Dict, List
import re

def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    description = base_description
    
    # Update Target Overhang
    target_overhang = target_terrain_config.get("target_overhang", 0.1)
    if target_overhang != 0.1:
        pattern = r"(- \*\*Goal\*\*: Reach x >= )(\d+\.?\d*)(m beyond the edge.)"
        description = re.sub(pattern, f"\\g<1>{target_overhang:.1f}m (originally 0.1m) \\g<3>", description)
    
    # Update Spawn Zone
    target_spawn = target_terrain_config.get("spawn_zone", [-10.0, 0.0])
    if target_spawn != [-10.0, 0.0]:
        pattern = r"(- \*\*Spawn Rule\*\*: Blocks must be initialized within the permitted build access zone \(typically x < 0.0, but may be further restricted: x in )(\[.*?\])(\)\.)"
        description = re.sub(pattern, f"\\g<1>[{target_spawn[0]:.1f}, {target_spawn[1]:.1f}] (originally [-10.0, 0.0])\\g<3>", description)
    
    # Update Ceiling Clearance
    target_ceiling = target_terrain_config.get("ceiling_y", 100.0)
    if target_ceiling != 100.0:
        pattern = r"(- \*\*Clearance\*\*: Watch out for overhead obstacles \(ceilings\) in some regions. Current clearance y: )(\d+\.?\d*)(m\.)"
        description = re.sub(pattern, f"\\g<1>{target_ceiling:.1f}m (originally 100.0m)\\g<3>", description)
        
    return description

def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    criteria = base_success_criteria
    
    # Update Reach in Success Criteria
    target_overhang = target_terrain_config.get("target_overhang", 0.1)
    if target_overhang != 0.1:
        pattern = r"(Tip reaches x > )(\d+\.?\d*)(m\))"
        criteria = re.sub(pattern, f"\\g<1>{target_overhang:.1f}m (originally 0.1m))", criteria)
        
    return criteria

def get_s06_curriculum_stages() -> List[Dict[str, Any]]:
    # Define the uniform suffix based on the union of all mutated variables
    UNIFORM_SUFFIX = """
Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - Atmospheric Wind: Lateral forces may exert pressure on the structure, potentially causing sliding or toppling.
 - Seismic Activity: The foundation may exhibit high-frequency oscillations, testing the dynamic stability of the assembly.
 - Vertical Clearance: Low-hanging barriers may restrict the height of your construction, forcing horizontal complexity and wedging strategies.
 - Gravitational Intensity: The magnitude of the downward pull may be significantly higher, increasing structural stress and friction requirements.
 - Table Inclination: The support surface may be tilted, introducing parallel gravitational components that encourage sliding towards or away from the edge.
 - Surface Friction: The table's grip may be altered, making standard anchoring techniques ineffective.
 - Build Access Zone: The region where blocks can be initialized may be further restricted, requiring greater cantilever extensions.

Discovery via feedback: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""

    return [
        {
            "stage_id": "Stage-1",
            "title": "The Gale-Force Anchor",
            "mutation_description": "Severe lateral wind force (-100.0) pushing away from the target. Requires significant mass to anchor the structure.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "target_overhang": 1.0,
                "spawn_zone": [-10.0, -1.0],
            },
            "physics_config": {
                "wind_force": -100.0,
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "The Resonating Ledge",
            "mutation_description": "Seismic oscillations combined with lateral wind. Tests stability against multi-directional forces.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "target_overhang": 1.2,
                "spawn_zone": [-10.0, -0.8],
                "oscillate": True,
                "osc_amplitude": 0.05,
                "osc_frequency": 5.0,
            },
            "physics_config": {
                "wind_force": -40.0,
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "The Titan's Narrow Gale",
            "mutation_description": "Increased gravity (2.5x) and severe wind, restricted by a low ceiling (0.5m). Limits vertical stacking for anchoring.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "target_overhang": 1.5,
                "spawn_zone": [-10.0, -0.5],
                "ceiling_y": 0.5,
            },
            "physics_config": {
                "gravity": (0, -25.0),
                "wind_force": -100.0,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "The Tilted Seismic Void",
            "mutation_description": "Extreme Gravity (5x), Table Tilt (-5 degrees), Slick Surface (0.2 friction), and Seismic Activity.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "target_overhang": 1.8,
                "spawn_zone": [-10.0, -0.2],
                "ceiling_y": 2.0,
                "table_angle": -5.0,
                "table_friction": 0.2,
                "oscillate": True,
                "osc_amplitude": 0.02,
                "osc_frequency": 3.0,
            },
            "physics_config": {
                "gravity": (0, -50.0),
                "wind_force": 20.0,
            },
        },
    ]
