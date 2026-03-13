"""
S-05: The Shelter task curriculum stages (mutations).
"""

from __future__ import annotations

from typing import Any, Dict, List
import re

# Base task defaults (must match environment.py and prompt.py)
DEFAULT_METEOR_COUNT = 12
DEFAULT_CORE_MAX_FORCE = 150.0
DEFAULT_MAX_MASS = 300.0
DEFAULT_METEOR_SPAWN_INTERVAL = 30
DEFAULT_WIND_FORCE = 0.0
DEFAULT_METEOR_RESTITUTION = 0.2
DEFAULT_METEOR_DENSITY = 5.0
DEFAULT_FLOOR_FRICTION = 0.5
DEFAULT_MAX_JOINT_FORCE = 1e12
DEFAULT_MAX_JOINT_TORQUE = 1e12


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    description = base_description
    
    # Update Mass Budget
    target_max_mass = target_terrain_config.get("max_structure_mass", DEFAULT_MAX_MASS)
    base_max_mass = base_terrain_config.get("max_structure_mass", DEFAULT_MAX_MASS)
    if target_max_mass != base_max_mass:
        mass_desc_pattern = r"(- \*\*Mass Budget\*\*: Total structure mass must be less than )(\d+\.?\d*) kg\."
        if re.search(mass_desc_pattern, description):
            description = re.sub(
                mass_desc_pattern,
                f"\\g<1>{target_max_mass:.1f} kg (originally < {base_max_mass:.1f} kg in the source environment).",
                description
            )

    # Update Core Position and Keep-Out Zone
    target_core_x = target_terrain_config.get("core_x", 10.0)
    target_core_y = target_terrain_config.get("core_y", 1.0)
    base_core_x = 10.0
    base_core_y = 1.0

    if target_core_x != base_core_x or target_core_y != base_core_y:
        # Update main description intro
        core_pos_pattern = r"(Protect a fragile Core \(a sensitive circular object at x=)(\d+\.?\d*)(, y=)(\d+\.?\d*)(\))"
        description = re.sub(core_pos_pattern, 
                            f"\\g<1>{target_core_x:.1f}\\g<3>{target_core_y:.1f} (originally x={base_core_x:.1f}, y={base_core_y:.1f})\\g<5>", 
                            description)
        
        # Update Task Environment Core section
        env_core_pattern = r"(- \*\*Core\*\*: A circular object centered at \()(\d+\.?\d*)(, )(\d+\.?\d*)(\)\.)"
        description = re.sub(env_core_pattern,
                            f"\\g<1>{target_core_x:.1f}\\g<3>{target_core_y:.1f}\\g<5> (originally centered at ({base_core_x:.1f}, {base_core_y:.1f}))",
                            description)

        # Update Keep-Out Zone constraint
        koz_pattern = r"(- \*\*Keep-Out Zone\*\*: You cannot build any structural components within 1.3m of the core center \()(\d+\.?\d*)(, )(\d+\.?\d*)(\)\.)"
        description = re.sub(koz_pattern,
                            f"\\g<1>{target_core_x:.1f}\\g<3>{target_core_y:.1f}\\g<5> (originally centered at ({base_core_x:.1f}, {base_core_y:.1f}))",
                            description)

    # Update Core Force threshold (VISIBLE)
    target_core_force = target_terrain_config.get("max_core_force", DEFAULT_CORE_MAX_FORCE)
    base_core_force = base_terrain_config.get("max_core_force", DEFAULT_CORE_MAX_FORCE)
    if target_core_force != base_core_force:
        description = re.sub(
            r"exceeds 150 N \(its structural tolerance\)",
            f"exceeds {target_core_force:.1f} N (originally {base_core_force:.1f} N in the source environment, its structural tolerance)",
            description
        )

    # Update Joint Limits (VISIBLE) in task description
    target_joint_force = float(target_terrain_config.get("max_joint_force", DEFAULT_MAX_JOINT_FORCE))
    base_joint_force = float(base_terrain_config.get("max_joint_force", DEFAULT_MAX_JOINT_FORCE))
    target_joint_torque = float(target_terrain_config.get("max_joint_torque", DEFAULT_MAX_JOINT_TORQUE))
    base_joint_torque = float(base_terrain_config.get("max_joint_torque", DEFAULT_MAX_JOINT_TORQUE))
    if target_joint_force != base_joint_force:
        description = re.sub(
            r"(maximum linear force )1e12( and maximum torque )",
            f"\\g<1>{target_joint_force:.1f} N (originally {base_joint_force:.1f} in the source environment)\\g<2>",
            description,
            count=1
        )
    if target_joint_torque != base_joint_torque:
        description = re.sub(
            r"maximum torque 1e12 Nm in the nominal mission",
            f"maximum torque {target_joint_torque:.1f} Nm (originally {base_joint_torque:.1f} in the source environment)",
            description,
            count=1
        )

    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    criteria = base_success_criteria
    
    # Update Mass Budget
    target_max_mass = target_terrain_config.get("max_structure_mass", DEFAULT_MAX_MASS)
    base_max_mass = base_terrain_config.get("max_structure_mass", DEFAULT_MAX_MASS)
    if target_max_mass != base_max_mass:
        mass_pattern = r"(- \*\*Mass Budget\*\*: < )(\d+\.?\d*) kg\."
        if re.search(mass_pattern, criteria):
            criteria = re.sub(
                mass_pattern,
                f"\\g<1>{target_max_mass:.1f} kg (originally < {base_max_mass:.1f} kg in the source environment).",
                criteria
            )

    # Update Keep-Out Zone Design Constraint
    target_core_x = target_terrain_config.get("core_x", 10.0)
    target_core_y = target_terrain_config.get("core_y", 1.0)
    base_core_x = 10.0
    base_core_y = 1.0

    if target_core_x != base_core_x or target_core_y != base_core_y:
        koz_criteria_pattern = r"(- \*\*Keep-Out Zone\*\*: Beam center distance to \()(\d+\.?\d*)(, )(\d+\.?\d*)(\) must be >= 1.3m\.)"
        criteria = re.sub(koz_criteria_pattern,
                         f"\\g<1>{target_core_x:.1f}\\g<3>{target_core_y:.1f}\\g<5> (originally distance to ({base_core_x:.1f}, {base_core_y:.1f}))",
                         criteria)

    # Update Core Force threshold in success criteria
    target_core_force = target_terrain_config.get("max_core_force", DEFAULT_CORE_MAX_FORCE)
    base_core_force = base_terrain_config.get("max_core_force", DEFAULT_CORE_MAX_FORCE)
    if target_core_force != base_core_force:
        criteria = re.sub(
            r"(peak impact force on the core must remain below )(\d+\.?\d*)( N\.)",
            f"\\g<1>{target_core_force:.1f} N (originally {base_core_force:.1f} N in the source environment)\\g<3>",
            criteria
        )
        criteria = re.sub(
            r"(Peak force on core < )(\d+\.?\d*)( N\.)",
            f"\\g<1>{target_core_force:.1f} N (originally {base_core_force:.1f} N in the source environment)\\g<3>",
            criteria
        )

    return criteria

# DYNAMICALLY GENERATED UNIFORM_SUFFIX based on the union of all mutated variables in Stages 1-4
# Tone: warn *what* might change only; never state exact values or direction of change.
UNIFORM_SUFFIX = """
Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - **Atmospheric Turbulence (Wind)**: Constant lateral forces may be acting on all objects, potentially blowing away unanchored or high-drag structures.
 - **Joint Shear Strength**: Connections may have limited linear load-bearing capacity and can fail under high-speed impacts or extreme lateral forces.
 - **Meteor Elasticity (Restitution)**: Falling debris may be highly elastic, causing unpredictable ricochets that can bypass standard overhead cover.
 - **Bombardment Intensity**: The total number of falling boulders may differ from the nominal environment, affecting duration and cumulative load of the storm.
 - **Core Fragility**: The central object may be exceptionally sensitive to even minor impacts, requiring near-perfect isolation.
 - **Mass Budget Scarcity**: The total allowed mass for construction may be restricted, forcing the use of lightweight materials.
 - **Joint Torque Tolerance**: Anchors and connections may have limited resistance to twisting forces, causing collapse under asymmetrical loads.
 - **Gravitational Constant**: The downward acceleration may differ from the nominal environment, affecting structural stress and impact energy.
 - **Lateral Boundaries (Containment)**: The scene may be enclosed by lateral walls, affecting boulder ricochets and airflow.

Discovery via feedback: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""

def get_s05_curriculum_stages() -> List[Dict[str, Any]]:
    return [
        {
            "stage_id": "Stage-1",
            "title": "The Gale Force",
            "mutation_description": "Strong lateral wind (-100.0) combined with limited joint strength (350N). Massive structures will experience enormous drag and snap their own anchors.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "wind_force": -100.0,
                "max_joint_force": 350.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "The Kinetic Ricochet",
            "mutation_description": "Extreme core sensitivity and a shifted core location. The core has been moved, requiring a completely different structural approach to ensure protection.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "core_x": 12.0,
                "core_y": 2.0,
                "meteor_restitution": 1.0,
                "floor_restitution": 1.0,
                "structure_restitution": 1.0,
                "floor_friction": 0.0,
                "structure_friction": 0.0,
                "meteor_vx_range": [-10.0, 10.0],
                "wind_force": 2.0,
                "meteor_count": 200,
                "max_core_force": 0.1,
                "has_walls": True,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "The Gravitational Constraint",
            "mutation_description": "High gravity (-60.0) combined with a strict mass limit (2.0kg) and robust joints. The structure must be incredibly light yet handle its own weight and high-energy impacts.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "max_structure_mass": 2.0,
                "max_joint_force": 100000.0,
                "max_joint_torque": 100000.0,
                "max_core_force": 300.0,
            },
            "physics_config": {
                "gravity": (0, -60.0),
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "The Celestial Infernal",
            "mutation_description": "Extreme lateral wind (50.0), a hyper-fragile core (10.0N), high gravity (-40.0), and low mass budget (5.0kg). A shifted core and contained environment make the original solution physically impossible to construct.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "core_x": 8.0,
                "core_y": 2.0,
                "wind_force": 50.0,
                "max_core_force": 10.0,
                "meteor_restitution": 0.9,
                "floor_restitution": 0.9,
                "structure_restitution": 0.9,
                "floor_friction": 0.0,
                "structure_friction": 0.0,
                "max_structure_mass": 5.0,
                "max_joint_force": 100000.0,
                "max_joint_torque": 100000.0,
                "has_walls": True,
            },
            "physics_config": {
                "gravity": (0, -40.0),
            },
        },
    ]
