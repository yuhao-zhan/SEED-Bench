"""
F-02: The Amphibian task curriculum stages (mutations).
Extreme difficulty and essential structural challenges.
"""
from __future__ import annotations
from typing import Any, Dict, List
import re

def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    description = base_description
    
    # Update thrust cooldown if it's considered a visible change
    default_cooldown = 3
    target_cooldown = int(target_terrain_config.get("thrust_cooldown_steps", default_cooldown))
    base_cooldown = int(base_terrain_config.get("thrust_cooldown_steps", default_cooldown))
    
    if target_cooldown != base_cooldown:
        cooldown_pattern = r"(\s*- \*\*Propulsion\*\*: .* \*\*Cooldown\*\*: Each component has a )(\d+)(-step cooldown between thrusts\.)"
        if re.search(cooldown_pattern, description):
            description = re.sub(
                cooldown_pattern,
                f"\\g<1>{target_cooldown}-step (originally {base_cooldown}-step in the source environment) cooldown between thrusts.",
                description
            )
            
    return description

def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    criteria = base_success_criteria
    
    # Update mass budget if it's considered a visible change
    default_mass = 600.0
    target_mass = float(target_terrain_config.get("max_structure_mass", default_mass))
    base_mass = float(base_terrain_config.get("max_structure_mass", default_mass))
    
    if target_mass != base_mass:
        mass_pattern = r"(\s*- \*\*Mass Budget\*\*: Total structure mass <= )(\d+)( kg\.)"
        if re.search(mass_pattern, criteria):
            criteria = re.sub(
                mass_pattern,
                f"\\g<1>{target_mass:.0f} kg (originally {base_mass:.0f} kg in the source environment).",
                criteria
            )

    # Update joint strength when max_joint_force is set or reverted (e.g. Stage-3 sets limit; Stage-1/2/4 have no limit)
    default_joint_force = float('inf')
    target_joint_force = target_terrain_config.get("max_joint_force", default_joint_force)
    base_joint_force = base_terrain_config.get("max_joint_force", default_joint_force)
    joint_limit_pattern = r"(- \*\*Joint Strength\*\*: Maximum force before shear is )(\d+\.?\d*)( N \(originally .+ in the source environment\)\.)"
    joint_no_limit_pattern = r"(- \*\*Joint Strength\*\*: Structural connections do not break under load \(no force limit\)\.)"
    # Reverted form (after going from finite limit back to no limit)
    joint_no_limit_with_origin_pattern = r"(- \*\*Joint Strength\*\*: Structural connections do not break under load \(no force limit\) \(originally .+ in the source environment\)\.)"

    if target_joint_force != base_joint_force:
        base_str = "no limit" if base_joint_force == float('inf') else f"{base_joint_force:.0f} N"
        if target_joint_force != float('inf'):
            # Target has a finite limit: show new limit (originally base value)
            if re.search(joint_no_limit_pattern, criteria):
                criteria = re.sub(
                    joint_no_limit_pattern,
                    f"- **Joint Strength**: Maximum force before shear is {target_joint_force:.0f} N (originally {base_str} in the source environment).",
                    criteria
                )
            elif re.search(joint_no_limit_with_origin_pattern, criteria):
                criteria = re.sub(
                    joint_no_limit_with_origin_pattern,
                    f"- **Joint Strength**: Maximum force before shear is {target_joint_force:.0f} N (originally {base_str} in the source environment).",
                    criteria
                )
            elif re.search(joint_limit_pattern, criteria):
                criteria = re.sub(
                    joint_limit_pattern,
                    f"\\g<1>{target_joint_force:.0f} N (originally {base_str} in the source environment).",
                    criteria
                )
        else:
            # Target has no limit: revert to no-force-limit wording (originally base value)
            if re.search(joint_limit_pattern, criteria):
                criteria = re.sub(
                    joint_limit_pattern,
                    f"- **Joint Strength**: Structural connections do not break under load (no force limit) (originally {base_str} in the source environment).",
                    criteria
                )

    return criteria

def get_f02_curriculum_stages() -> List[Dict[str, Any]]:
    # DYNAMICALLY GENERATED UNION OF VARIABLES ACROSS STAGE 1-4
    UNIFORM_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Electromagnetic Deadzone**: A regional field that completely disables all propulsion systems when a component enters it.
- **Corrosive Altitude Ceiling**: A toxic atmospheric layer above the water that applies catastrophic downward crushing forces to any elevated structures.
- **Abyssal Whirlpools**: Localized vortexes in the water channel that generate extreme downward suction on submerged or floating masses.
- **Opposing Current**: The magnitude of the water's flow against the direction of travel may be altered.
- **Joint Strength**: The maximum stress a structural connection can withstand before shearing.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""

    return [
        {
            "stage_id": "Stage-1",
            "title": "The Silent Expanse",
            "mutation_description": "A wide EMP field disables all thrust in the center of the river. Requires a multi-segment bridge-like train to push/pull through the deadzone.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "emp_zone": [14.0, 18.0], # 4m wide deadzone
                "current_per_kg": 25.0, # Increased current so heavy baseline stalls in EMP
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "The Low Ceiling",
            "mutation_description": "A toxic atmosphere prevents flight. Strong current demands high horizontal power while staying low.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "corrosive_y": 2.5, # Water surface is 2.0. Must stay very low.
                "current_per_kg": 60.0, # High current requires massive horizontal thrust
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "The Maelstrom",
            "mutation_description": "A violent whirlpool pulls vehicles down. Weak joints prevent rigid brute-force bridging.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "whirlpool": {"x": 17.0, "width": 4.0, "force": 200.0},
                "max_joint_force": 200.0, # Joints snap if pulled unevenly
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "The Gauntlet of Contradictions",
            "mutation_description": "Combines EMP, low ceiling, and whirlpools into an ultimate paradox.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "emp_zone": [14.0, 16.0], # 2m EMP
                "corrosive_y": 2.7, # Can't fly
                "whirlpool": {"x": 21.0, "width": 3.0, "force": 150.0}, # Pulled down
                "current_per_kg": 20.0, # Pushed back
            },
            "physics_config": {},
        },
    ]
