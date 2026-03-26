"""
S-05: The Shelter task curriculum stages (mutations).
"""

from __future__ import annotations

from typing import Any, Dict, List
import re

# Base task defaults (must match environment.py and prompt.py)
DEFAULT_METEOR_COUNT = 12
DEFAULT_CORE_MAX_FORCE = 150.0
DEFAULT_CORE_X = 10.0
DEFAULT_CORE_Y = 1.0
DEFAULT_MAX_MASS = 300.0
DEFAULT_METEOR_SPAWN_INTERVAL = 30
DEFAULT_WIND_FORCE = 0.0
DEFAULT_METEOR_RESTITUTION = 0.2
DEFAULT_METEOR_DENSITY = 5.0
DEFAULT_FLOOR_FRICTION = 0.5
DEFAULT_MAX_JOINT_FORCE = 1e12
DEFAULT_MAX_JOINT_TORQUE = 1e12
DEFAULT_HAS_WALLS = False


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    description = base_description

    # Update Bombardment (meteor count and spawn interval) when mutated
    target_meteor_count = int(target_terrain_config.get("meteor_count", DEFAULT_METEOR_COUNT))
    base_meteor_count = int(base_terrain_config.get("meteor_count", DEFAULT_METEOR_COUNT))
    target_spawn_interval = int(target_terrain_config.get("meteor_spawn_interval", DEFAULT_METEOR_SPAWN_INTERVAL))
    base_spawn_interval = int(base_terrain_config.get("meteor_spawn_interval", DEFAULT_METEOR_SPAWN_INTERVAL))
    if target_meteor_count != base_meteor_count or target_spawn_interval != base_spawn_interval:
        # Match prompt: "... simulation steps), and 4 additional ..." (comma after ")")
        boulder_pattern = r"(In the nominal mission, )(\d+)( boulders spawn from above \(one every )(\d+)( simulation steps\))(?:, and 4 additional boulders spawn from the left and right sides \(every 90 steps\)\.)"
        if re.search(boulder_pattern, description):
            side_count = target_meteor_count // 3
            side_interval = target_spawn_interval * 3
            base_side_count = base_meteor_count // 3
            base_side_interval = base_spawn_interval * 3
            description = re.sub(
                boulder_pattern,
                f"\\g<1>{target_meteor_count} boulders spawn from above (one every {target_spawn_interval} simulation steps) (originally {base_meteor_count} boulders, one every {base_spawn_interval} simulation steps in the source environment), and {side_count} additional boulders spawn from the left and right sides (every {side_interval} steps) (originally {base_side_count} additional boulders, every {base_side_interval} steps in the source environment).",
                description,
                count=1,
            )
        
        # Update evaluation threshold mention: (i.e. at least meteor_count × spawn_interval steps, whichever is larger)
        eval_pattern = r"\(i\.e\. at least meteor_count × spawn_interval steps, whichever is larger\)"
        description = re.sub(eval_pattern,
                           f"(i.e. at least {target_meteor_count * target_spawn_interval} steps (originally {base_meteor_count * base_spawn_interval} steps in the source environment), whichever is larger)",
                           description)

    # Update Mass Budget
    target_max_mass = target_terrain_config.get("max_structure_mass", DEFAULT_MAX_MASS)
    base_max_mass = base_terrain_config.get("max_structure_mass", DEFAULT_MAX_MASS)
    if target_max_mass != base_max_mass:
        mass_desc_pattern = r"(- \*\*Mass Budget\*\*: Total structure mass must be <= )(\d+\.?\d*) kg\."
        if re.search(mass_desc_pattern, description):
            description = re.sub(
                mass_desc_pattern,
                f"\\g<1>{target_max_mass:.1f} kg (originally {base_max_mass:.1f} kg in the source environment).",
                description
            )

    # Update Height Limit
    target_max_height = target_terrain_config.get("max_structure_height", 7.5) # Default from environment.py
    base_max_height = base_terrain_config.get("max_structure_height", 7.5)
    if target_max_height != base_max_height:
        height_pattern = r"(- \*\*Height Limit\*\*: No beam center or joint anchor may be above y=)(\d+\.?\d*)m\."
        description = re.sub(height_pattern,
                            f"\\g<1>{target_max_height:.1f}m (originally y={base_max_height:.1f}m in the source environment).",
                            description)

    # Update Build Zone
    target_bx_min = target_terrain_config.get("build_zone_x_min", 5.0)
    target_bx_max = target_terrain_config.get("build_zone_x_max", 15.0)
    target_by_min = target_terrain_config.get("build_zone_y_min", 0.0)
    target_by_max = target_terrain_config.get("build_zone_y_max", 8.0)
    base_bx_min = base_terrain_config.get("build_zone_x_min", 5.0)
    base_bx_max = base_terrain_config.get("build_zone_x_max", 15.0)
    base_by_min = base_terrain_config.get("build_zone_y_min", 0.0)
    base_by_max = base_terrain_config.get("build_zone_y_max", 8.0)

    if (target_bx_min != base_bx_min or target_bx_max != base_bx_max or 
        target_by_min != base_by_min or target_by_max != base_by_max):
        bz_pattern1 = r"(Structure must be built within x=\[)(\d+\.?\d*)(, )(\d+\.?\d*)(\] m and y=\[)(\d+\.?\d*)(, )(\d+\.?\d*)(\] m)"
        description = re.sub(bz_pattern1,
                            f"\\g<1>{target_bx_min:.1f}\\g<3>{target_bx_max:.1f}\\g<5>{target_by_min:.1f}\\g<7>{target_by_max:.1f}\\g<9> (originally x=[{base_bx_min:.1f}, {base_bx_max:.1f}] m and y=[{base_by_min:.1f}, {base_by_max:.1f}] m in the source environment)",
                            description)
        
        bz_pattern2 = r"(- \*\*Build Zone\*\*: All beam centers and joint anchors must lie within x=\[)(\d+\.?\d*)(, )(\d+\.?\d*)(\] m, y=\[)(\d+\.?\d*)(, )(\d+\.?\d*)(\] m\.)"
        description = re.sub(bz_pattern2,
                            f"\\g<1>{target_bx_min:.1f}\\g<3>{target_bx_max:.1f}\\g<5>{target_by_min:.1f}\\g<7>{target_by_max:.1f}\\g<9> (originally x=[{base_bx_min:.1f}, {base_bx_max:.1f}] m, y=[{base_by_min:.1f}, {base_by_max:.1f}] m in the source environment).",
                            description)

    # Update Core Position and Keep-Out Zone
    target_core_x = target_terrain_config.get("core_x", DEFAULT_CORE_X)
    target_core_y = target_terrain_config.get("core_y", DEFAULT_CORE_Y)
    base_core_x = base_terrain_config.get("core_x", DEFAULT_CORE_X)
    base_core_y = base_terrain_config.get("core_y", DEFAULT_CORE_Y)

    if target_core_x != base_core_x or target_core_y != base_core_y:
        # Update main description intro: [new_value] (originally [old_value] in the source environment). Consume " from" so the sentence continues as "... environment). From heavy falling ...".
        core_pos_pattern = r"(Protect a fragile Core \(a sensitive circular object at x=)(\d+\.?\d*)(, y=)(\d+\.?\d*)(\) from)"
        description = re.sub(core_pos_pattern,
                            f"\\g<1>{target_core_x:.1f}\\g<3>{target_core_y:.1f}) (originally x={base_core_x:.1f}, y={base_core_y:.1f} in the source environment) from",
                            description)

        # Update Task Environment Core section: no period between new value and (originally ...)
        env_core_pattern = r"(- \*\*Core\*\*: A circular object with a radius of 0\.5m centered at \()(\d+\.?\d*)(, )(\d+\.?\d*)(\)\.)"
        description = re.sub(env_core_pattern,
                            f"\\g<1>{target_core_x:.1f}\\g<3>{target_core_y:.1f}) (originally centered at ({base_core_x:.1f}, {base_core_y:.1f}) in the source environment). ",
                            description)

        # Update Keep-Out Zone constraint: no period between new value and (originally ...)
        koz_pattern = r"(- \*\*Keep-Out Zone\*\*: You cannot build any structural components within 1.3m of the core center \()(\d+\.?\d*)(, )(\d+\.?\d*)(\)\.)"
        description = re.sub(koz_pattern,
                            f"\\g<1>{target_core_x:.1f}\\g<3>{target_core_y:.1f}) (originally centered at ({base_core_x:.1f}, {base_core_y:.1f}) in the source environment). ",
                            description)

    # Update Core Force threshold (VISIBLE)
    target_core_force = target_terrain_config.get("max_core_force", DEFAULT_CORE_MAX_FORCE)
    base_core_force = base_terrain_config.get("max_core_force", DEFAULT_CORE_MAX_FORCE)
    if target_core_force != base_core_force:
        description = re.sub(
            r"exceeds (\d+\.?\d*) N \(its structural tolerance\)\.",
            f"exceeds {target_core_force:.1f} N (its structural tolerance) (originally {base_core_force:.1f} N in the source environment).",
            description
        )

    # Update Joint Limits (VISIBLE) in task description
    target_joint_force = float(target_terrain_config.get("max_joint_force", DEFAULT_MAX_JOINT_FORCE))
    base_joint_force = float(base_terrain_config.get("max_joint_force", DEFAULT_MAX_JOINT_FORCE))
    target_joint_torque = float(target_terrain_config.get("max_joint_torque", DEFAULT_MAX_JOINT_TORQUE))
    base_joint_torque = float(base_terrain_config.get("max_joint_torque", DEFAULT_MAX_JOINT_TORQUE))
    # Match any numeric representation (1e12, 1e+12, 1000000000000, etc.) for robustness
    _num = r"\d+(?:\.\d+)?(?:e\+?\d+)?"
    if target_joint_force != base_joint_force:
        description = re.sub(
            rf"(maximum linear force ){_num} N( and maximum torque )",
            f"\\g<1>{target_joint_force:.1f} N (originally {base_joint_force:.1f} N in the source environment)\\g<2>",
            description,
            count=1
        )
    if target_joint_torque != base_joint_torque:
        description = re.sub(
            rf"maximum torque {_num} Nm in the nominal mission",
            f"maximum torque {target_joint_torque:.1f} Nm (originally {base_joint_torque:.1f} Nm in the source environment) in the nominal mission",
            description,
            count=1
        )

    # Update Lateral boundaries (has_walls) when mutated
    target_has_walls = bool(target_terrain_config.get("has_walls", DEFAULT_HAS_WALLS))
    base_has_walls = bool(base_terrain_config.get("has_walls", DEFAULT_HAS_WALLS))
    if target_has_walls != base_has_walls:
        if target_has_walls:
            description = re.sub(
                r"(- \*\*Lateral boundaries\*\*: )The scene has no lateral containment walls; the build zone is open at the sides\.",
                r"\g<1>The scene is enclosed by lateral walls (originally no lateral containment walls in the source environment).",
                description
            )
        else:
            description = re.sub(
                r"(- \*\*Lateral boundaries\*\*: )The scene is enclosed by lateral walls \(originally no lateral containment walls in the source environment\)\.",
                r"\g<1>The scene has no lateral containment walls; the build zone is open at the sides (originally enclosed by lateral walls in the source environment).",
                description
            )

    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    criteria = base_success_criteria
    
    # Update Mass Budget
    target_max_mass = target_terrain_config.get("max_structure_mass", DEFAULT_MAX_MASS)
    base_max_mass = base_terrain_config.get("max_structure_mass", DEFAULT_MAX_MASS)
    if target_max_mass != base_max_mass:
        mass_pattern = r"(- \*\*Mass Budget\*\*: <= )(\d+\.?\d*) kg\."
        if re.search(mass_pattern, criteria):
            criteria = re.sub(
                mass_pattern,
                f"\\g<1>{target_max_mass:.1f} kg (originally {base_max_mass:.1f} kg in the source environment).",
                criteria
            )

    # Update Build Zone Design Constraint
    target_bx_min = target_terrain_config.get("build_zone_x_min", 5.0)
    target_bx_max = target_terrain_config.get("build_zone_x_max", 15.0)
    target_by_min = target_terrain_config.get("build_zone_y_min", 0.0)
    target_by_max = target_terrain_config.get("build_zone_y_max", 8.0)
    base_bx_min = base_terrain_config.get("build_zone_x_min", 5.0)
    base_bx_max = base_terrain_config.get("build_zone_x_max", 15.0)
    base_by_min = base_terrain_config.get("build_zone_y_min", 0.0)
    base_by_max = base_terrain_config.get("build_zone_y_max", 8.0)
    if (target_bx_min != base_bx_min or target_bx_max != base_bx_max or 
        target_by_min != base_by_min or target_by_max != base_by_max):
        bz_crit_pattern = r"(- \*\*Build Zone\*\*: Beam centers and joint anchors within x=\[)(\d+\.?\d*)(, )(\d+\.?\d*)(\] m, y=\[)(\d+\.?\d*)(, )(\d+\.?\d*)(\] m\.)"
        criteria = re.sub(bz_crit_pattern,
                         f"\\g<1>{target_bx_min:.1f}\\g<3>{target_bx_max:.1f}\\g<5>{target_by_min:.1f}\\g<7>{target_by_max:.1f}\\g<9> (originally x=[{base_bx_min:.1f}, {base_bx_max:.1f}] m, y=[{base_by_min:.1f}, {base_by_max:.1f}] m in the source environment).",
                         criteria)

    # Update Height Limit Design Constraint
    target_max_height = target_terrain_config.get("max_structure_height", 7.5)
    base_max_height = base_terrain_config.get("max_structure_height", 7.5)
    if target_max_height != base_max_height:
        height_crit_pattern = r"(- \*\*Height Limit\*\*: No beam center or joint anchor may be above y=)(\d+\.?\d*)m\."
        criteria = re.sub(height_crit_pattern,
                         f"\\g<1>{target_max_height:.1f}m (originally y={base_max_height:.1f}m in the source environment).",
                         criteria)

    # Update Keep-Out Zone Design Constraint
    target_core_x = target_terrain_config.get("core_x", DEFAULT_CORE_X)
    target_core_y = target_terrain_config.get("core_y", DEFAULT_CORE_Y)
    base_core_x = base_terrain_config.get("core_x", DEFAULT_CORE_X)
    base_core_y = base_terrain_config.get("core_y", DEFAULT_CORE_Y)

    if target_core_x != base_core_x or target_core_y != base_core_y:
        koz_criteria_pattern = r"(- \*\*Keep-Out Zone\*\*: Beam center distance to \()(\d+\.?\d*)(, )(\d+\.?\d*)(\) must be >= 1.3m\.)"
        criteria = re.sub(koz_criteria_pattern,
                         f"\\g<1>{target_core_x:.1f}\\g<3>{target_core_y:.1f}) must be >= 1.3m (originally distance to ({base_core_x:.1f}, {base_core_y:.1f}) in the source environment).",
                         criteria)

    # Update Core Force threshold in success criteria
    target_core_force = target_terrain_config.get("max_core_force", DEFAULT_CORE_MAX_FORCE)
    base_core_force = base_terrain_config.get("max_core_force", DEFAULT_CORE_MAX_FORCE)
    if target_core_force != base_core_force:
        criteria = re.sub(
            r"(peak impact force on the core must remain <= )(\d+\.?\d*)( N\.)",
            f"\\g<1>{target_core_force:.1f} N (originally {base_core_force:.1f} N in the source environment).",
            criteria
        )
        criteria = re.sub(
            r"(Peak force on core <= )(\d+\.?\d*)( N\.)",
            f"\\g<1>{target_core_force:.1f} N (originally {base_core_force:.1f} N in the source environment).",
            criteria
        )

    # Update Lateral boundaries (has_walls) in success criteria
    target_has_walls = bool(target_terrain_config.get("has_walls", DEFAULT_HAS_WALLS))
    base_has_walls = bool(base_terrain_config.get("has_walls", DEFAULT_HAS_WALLS))
    if target_has_walls != base_has_walls:
        if target_has_walls:
            criteria = re.sub(
                r"(- \*\*Lateral boundaries\*\*: )The scene has no lateral containment walls\.",
                r"\g<1>The scene is enclosed by lateral walls (originally no lateral containment walls in the source environment).",
                criteria
            )
        else:
            criteria = re.sub(
                r"(- \*\*Lateral boundaries\*\*: )The scene is enclosed by lateral walls \(originally no lateral containment walls in the source environment\)\.",
                r"\g<1>The scene has no lateral containment walls (originally enclosed by lateral walls in the source environment).",
                criteria
            )

    # Update Joint Limits in success criteria
    target_joint_force = float(target_terrain_config.get("max_joint_force", DEFAULT_MAX_JOINT_FORCE))
    base_joint_force = float(base_terrain_config.get("max_joint_force", DEFAULT_MAX_JOINT_FORCE))
    target_joint_torque = float(target_terrain_config.get("max_joint_torque", DEFAULT_MAX_JOINT_TORQUE))
    base_joint_torque = float(base_terrain_config.get("max_joint_torque", DEFAULT_MAX_JOINT_TORQUE))
    _num = r"\d+(?:\.\d+)?(?:e\+?\d+)?"
    if target_joint_force != base_joint_force:
        criteria = re.sub(
            rf"(Max force <= ){_num}( N)",
            f"\\g<1>{target_joint_force:.1f}\\g<2> (originally {base_joint_force:.1f} N in the source environment)",
            criteria,
            count=1
        )
    if target_joint_torque != base_joint_torque:
        criteria = re.sub(
            rf"(max torque <= ){_num}( Nm)",
            f"\\g<1>{target_joint_torque:.1f}\\g<2> (originally {base_joint_torque:.1f} Nm in the source environment)",
            criteria,
            count=1
        )

    return criteria

# DYNAMICALLY GENERATED UNIFORM_SUFFIX based on the union of all mutated variables in Stages 1-4
# Union of mutated variables: max_joint_force, max_joint_torque, wind_force, max_structure_mass,
# meteor_restitution, has_walls, gravity, max_core_force, core_x (core_y unused but in union)
UNIFORM_SUFFIX = """
Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - **Joint Shear Strength (Fragile Anchor Points)**: The maximum linear force and torque that connections can withstand may differ from the nominal environment; joints may fail if limits are exceeded.
 - **Atmospheric Turbulence (Wind)**: Constant lateral forces may act on all bodies, pushing structures sideways and requiring robust bracing or low drag to avoid sliding or tipping.
 - **Mass Budget**: The total allowed mass for construction may differ from the nominal environment.
 - **Meteor Elasticity (Restitution)**: Falling debris elasticity may differ from nominal, affecting ricochets and secondary impacts.
 - **Lateral Boundaries (Containment)**: The scene may be enclosed by lateral walls, amplifying ricochets and horizontal debris paths.
 - **Gravitational Constant**: Downward acceleration may differ from nominal; structural loads and impact energy may be affected.
 - **Core Fragility**: The protected object's impact tolerance may differ from nominal.
 - **Core Position**: The location of the protected object may differ from the nominal environment, requiring different structural placement and coverage.
 - **Initial Conditions (Random Seed)**: The exact spawn positions and initial velocities of incoming meteors may differ from the nominal environment.

Discovery via feedback: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""

def get_s05_curriculum_stages() -> List[Dict[str, Any]]:
    return [
        {
            "stage_id": "Stage-1",
            "title": "The Fragile Anchor",
            "mutation_description": "Joints and ground anchors have severely reduced shear and torque capacity. A standard heavy shelter concentrates impact loads into few weld joints; when any reaction force or torque exceeds the hidden limit, that joint fails and the structure collapses. The agent must discover the failure mode from feedback and redesign so loads are distributed (e.g. more joints, lighter members, or geometry that keeps no single connection above the threshold).",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "max_joint_force": 5000.0,
                "max_joint_torque": 1e12,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "The Shifting Center",
            "mutation_description": "The protected core is displaced to a non-central position. The standard symmetric shelter leaves the core outside its coverage or in a weak spot; the agent must discover the new position from feedback and relocate the structure.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "core_x": 5.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "The Ricochet Crucible",
            "mutation_description": "Tight mass budget, fragile joints, highly elastic meteors, and lateral walls create conflicting constraints: minimal mass, joint-safe geometry, and deflection of ricochets that bounce off walls.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "max_structure_mass": 2.0,
                "max_joint_force": 8000.0,
                "max_joint_torque": 8000.0,
                "max_core_force": 350.0,
                "meteor_restitution": 0.95,
                "has_walls": True,
                "seed": 123,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "The Gravitational Void",
            "mutation_description": "High gravity, hyper-sensitive core at shifted position, opposing wind, walls, elastic meteors, and tight mass and joint limits. The agent must balance impact isolation, lateral stability, and structural survival.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "core_x": 13.0,
                "max_core_force": 250.0,
                "max_structure_mass": 4.0,
                "wind_force": -45.0,
                "has_walls": True,
                "meteor_restitution": 0.9,
                "max_joint_force": 12000.0,
                "max_joint_torque": 13500.0,
            },
            "physics_config": {
                "gravity": (0, -60.0),
            },
        },
    ]
