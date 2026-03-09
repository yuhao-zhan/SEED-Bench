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
    # Only INVISIBLE variables are listed here. VISIBLE variables (Overhang, Spawn Zone, Ceiling) 
    # are explicitly updated in the main prompt body.
    UNIFORM_SUFFIX = """
Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - Surface Friction: The table's grip may be severely compromised, making standard anchoring techniques ineffective and causing the structure to slide under minimal load.
 - Atmospheric Wind: Powerful lateral forces may exert constant pressure on the structure, pushing it away from or towards the edge.
 - Seismic Activity: The foundation may exhibit high-frequency oscillations, testing the dynamic stability and structural integrity of your assembly.
 - Gravitational Intensity: The magnitude of the downward pull may be significantly higher, increasing structural stress and magnifying the effects of any imbalance.
 - Table Inclination: The support surface may be tilted, introducing parallel gravitational components that encourage sliding and complicate the center of mass calculation.

Discovery via feedback: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""

    return [
        {
            "stage_id": "Stage-1",
            "title": "The Slick Threshold",
            "mutation_description": "Extremely low table friction (0.05). Requires precise balancing and high mass to prevent sliding even without external forces.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "target_overhang": 1.2,
                "spawn_zone": [-10.0, -0.8],
                "table_friction": 0.05,
            },
            "physics_config": {
                "gravity": (0, -10.0),
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "The Heavy Gale",
            "mutation_description": "Powerful lateral wind force (-400.0) pushing away from the edge. Requires significant mass and friction to anchor the base.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "target_overhang": 1.5,
                "spawn_zone": [-10.0, -0.5],
            },
            "physics_config": {
                "wind_force": -400.0,
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "The Shaking Ceiling",
            "mutation_description": "Low vertical clearance (0.8m) combined with seismic oscillations and wind. Prevents vertical anchoring and tests dynamic stability.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "target_overhang": 1.8,
                "spawn_zone": [-10.0, -0.2],
                "ceiling_y": 0.8,
                "oscillate": True,
                "osc_amplitude": 0.02,
                "osc_frequency": 3.0,
            },
            "physics_config": {
                "wind_force": -100.0,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "The Tilted Titan",
            "mutation_description": "Multi-variable challenge: High Gravity (5x), Tilted Slick Surface (-5 deg, 0.05 friction), and Extreme Lateral Wind (-800.0).",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "target_overhang": 1.8,
                "spawn_zone": [-10.0, 0.0],
                "table_angle": -5.0,
                "table_friction": 0.05,
            },
            "physics_config": {
                "gravity": (0, -50.0),
                "wind_force": -800.0,
            },
        },
    ]
