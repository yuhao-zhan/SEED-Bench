"""
S-06: The Overhang task curriculum stages (mutations).
Redesigned for extreme difficulty requiring multi-block structural optimization.
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
        description = re.sub(pattern, f"\\g<1>{target_overhang:.2f}m (originally 0.1m) \\g<3>", description)
    
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
        
    # Update Mass Budget
    target_mass = target_terrain_config.get("max_total_mass", 20000.0)
    if target_mass != 20000.0:
        pattern = r"(- \*\*Mass Budget\*\*: Total structure mass must be less than )(\d+\.?\d*)( units\.)"
        description = re.sub(pattern, f"\\g<1>{target_mass:.1f} units (originally 20000.0 units)\\g<3>", description)
        
    return description

def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    criteria = base_success_criteria
    
    # Update Reach in Success Criteria
    target_overhang = target_terrain_config.get("target_overhang", 0.1)
    if target_overhang != 0.1:
        pattern = r"(\(Tip reaches x > )(\d+\.?\d*)(m\))"
        criteria = re.sub(pattern, f"\\g<1>{target_overhang:.2f}m (originally 0.1m))", criteria)
        
    # Update Mass Budget in constraints
    target_mass = target_terrain_config.get("max_total_mass", 20000.0)
    if target_mass != 20000.0:
        pattern = r"(- \*\*Mass Budget\*\*: Total mass must be <= )(\d+\.?\d*)( units\.)"
        criteria = re.sub(pattern, f"\\g<1>{target_mass:.1f} units (originally 20000.0 units)\\g<3>", criteria)
        
    return criteria

def get_s06_curriculum_stages() -> List[Dict[str, Any]]:
    # Define the uniform suffix based on the union of all mutated variables
    UNIFORM_SUFFIX = """
Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - Gravitational Intensity: The magnitude of the downward pull may be significantly higher, increasing structural stress and magnifying the effects of any imbalance.
 - Surface Friction: The table's grip may be severely compromised, making standard anchoring techniques ineffective and causing the structure to slide under minimal load.
 - Atmospheric Wind: Powerful lateral forces may exert constant pressure on the structure, pushing it away from or towards the edge.
 - Table Inclination: The support surface may be tilted, introducing parallel gravitational components that encourage sliding and complicate the center of mass calculation.
 - Vertical Clearance: Overhead obstacles may restrict the height of your structure, preventing high stacking or certain counterweight designs.
 - Seismic Activity: The foundation may exhibit high-frequency oscillations, testing the dynamic stability and structural integrity of your assembly.

Discovery via feedback: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""

    return [
        {
            "stage_id": "Stage-1",
            "title": "The Harmonic Horizon",
            "mutation_description": "Fundamental Structural Challenge: Reach 0.8m overhang using 1.0m blocks.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "target_overhang": 0.8,
                "spawn_zone": [-10.0, 0.4],
            },
            "physics_config": {
                "gravity": (0, -10.0),
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "The Slipstream Stacks",
            "mutation_description": "Structural + Physics: Reach 1.0m overhang with very low table friction (0.1).",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "target_overhang": 1.0,
                "spawn_zone": [-10.0, 0.6],
                "table_friction": 0.1,
            },
            "physics_config": {
                "gravity": (0, -10.0),
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "The High-Gravity Reach",
            "mutation_description": "Structural + Physics: Reach 1.2m overhang under High Gravity (2x).",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "target_overhang": 1.2,
                "spawn_zone": [-10.0, 0.8],
            },
            "physics_config": {
                "gravity": (0, -20.0),
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "The Hurricane Reach",
            "mutation_description": "The Ultimate Test: Reach 1.5m overhang with Lateral Wind (1.0).",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "target_overhang": 1.5,
                "spawn_zone": [-10.0, 1.1],
            },
            "physics_config": {
                "gravity": (0, -10.0),
                "wind_force": 1.0,
            },
        },
    ]
