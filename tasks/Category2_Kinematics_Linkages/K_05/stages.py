"""
K-05: The Lifter task curriculum stages (mutations).

All stage definitions live under tasks/Category2_Kinematics_Linkages/K_05.
The solver agent is NOT told exact invisible parameter changes; it must infer from feedback.
"""

from __future__ import annotations

from typing import Any, Dict, List
import re


def update_task_description_for_visible_changes(
    base_description: str,
    target_terrain_config: Dict[str, Any],
    base_terrain_config: Dict[str, Any],
    target_physics_config: Dict[str, Any] = None,
    base_physics_config: Dict[str, Any] = None,
    *,
    stage: Dict[str, Any] = None,
) -> str:
    """
    Update task description to reflect visible physical changes.
    Format: [new_value] (originally [old_value] in the source environment).
    Callers may pass stage=stage so that physics_config is taken from the stage dict.
    """
    description = base_description
    target_physics_config = target_physics_config or {}
    base_physics_config = base_physics_config or {}
    if stage is not None:
        target_physics_config = dict(stage.get("physics_config") or {})
        base_physics_config = {}
    target_y = target_terrain_config.get("target_object_y", 9.0)
    base_y = base_terrain_config.get("target_object_y", 9.0)
    target_obj = target_terrain_config.get("object", {})
    base_obj = base_terrain_config.get("object", {})
    target_mass = float(target_obj.get("mass", 20.0))
    base_mass = float(base_obj.get("mass", 20.0))
    target_obj_friction = float(target_obj.get("friction", 0.6))
    base_obj_friction = float(base_obj.get("friction", 0.6))
    default_sustain_s = 3.0
    default_max_structure_mass = 60.0
    target_sustain_s = float(target_terrain_config.get("min_sustain_s", default_sustain_s))
    base_sustain_s = float(base_terrain_config.get("min_sustain_s", default_sustain_s))
    target_max_mass = float(target_terrain_config.get("max_structure_mass", default_max_structure_mass))
    base_max_mass = float(base_terrain_config.get("max_structure_mass", default_max_structure_mass))
    target_ground_friction = float(target_terrain_config.get("ground_friction", 0.8))
    base_ground_friction = float(base_terrain_config.get("ground_friction", 0.8))

    if target_y != base_y:
        # Update "at least y=9.0m"
        pattern = r"(at least y=)(\d+\.?\d*)m"
        description = re.sub(pattern, f"\\g<1>{target_y:.1f}m (originally y={base_y:.1f}m in the source environment)", description)
        # Update "Object center reaches y >= 9.0m" (constraints section)
        pattern_y_ge = r"(reaches y >= )(\d+\.?\d*)m"
        description = re.sub(pattern_y_ge, f"\\g<1>{target_y:.1f}m (originally y >= {base_y:.1f}m in the source environment)", description)

    if target_mass != base_mass:
        # Update "A 20 kg block" or "A 20 kg block (0.6 m × 0.4 m, ...)" (target object mass); allow optional ", friction coefficient X.X"
        mass_pattern = r"(- \*\*Target Object\*\*: A )(\d+\.?\d*)( kg)( block(?: \([\d.]+ m × [\d.]+ m, width × height\))?(?:, friction coefficient [\d.]+)?, resting at x=)"
        if re.search(mass_pattern, description):
            description = re.sub(
                mass_pattern,
                f"\\g<1>{target_mass:.0f} kg (originally {base_mass:.0f} kg in the source environment)\\g<4>",
                description,
            )

    if target_ground_friction != base_ground_friction:
        # Update "friction coefficient 0.8" for Ground
        ground_friction_pattern = r"(- \*\*Ground\*\*: A flat horizontal surface at y=1\.0m \()(friction coefficient )(\d+\.?\d*)(\)\.)"
        if re.search(ground_friction_pattern, description):
            description = re.sub(
                ground_friction_pattern,
                f"\\g<1>\\g<2>{target_ground_friction:.1f} (originally {base_ground_friction:.1f} in the source environment).",
                description,
            )

    if target_obj_friction != base_obj_friction:
        # Update "friction coefficient 0.6" for Target Object
        friction_pattern = r"(friction coefficient )(\d+\.?\d*)(, resting at x=)"
        if re.search(friction_pattern, description):
            description = re.sub(
                friction_pattern,
                f"\\g<1>{target_obj_friction:.1f} (originally {base_obj_friction:.1f} in the source environment), resting at x=",
                description,
            )

    if target_sustain_s != base_sustain_s:
        # Update "for at least 3.0 seconds" in constraints
        sustain_pattern = r"(for at least )(\d+\.?\d*)( seconds \()"
        if re.search(sustain_pattern, description):
            description = re.sub(
                sustain_pattern,
                f"\\g<1>{target_sustain_s:.1f} seconds (originally {base_sustain_s:.1f} seconds in the source environment) (",
                description,
            )

    if target_max_mass != base_max_mass:
        # Update "must be less than 60 kg" in constraints
        mass_budget_pattern = r"(Total structure mass must be less than )(\d+\.?\d*)( kg\.)"
        if re.search(mass_budget_pattern, description):
            description = re.sub(
                mass_budget_pattern,
                f"\\g<1>{target_max_mass:.0f} kg (originally {base_max_mass:.0f} kg in the source environment).",
                description,
            )

    # Ceiling: if target has ceiling_gap, update "Ceiling: None (...)" or existing "Gap at ..." to actual dimensions
    target_ceiling = target_terrain_config.get("ceiling_gap")
    base_ceiling = base_terrain_config.get("ceiling_gap")
    if target_ceiling:
        c_y = target_ceiling.get("y", 6.0)
        c_x_min = target_ceiling.get("x_min", 3.0)
        c_x_max = target_ceiling.get("x_max", 5.0)
        gap_width = c_x_max - c_x_min
        ceiling_new = f"Gap at y={c_y:.1f}m, x=[{c_x_min:.1f}, {c_x_max:.1f}] (gap width {gap_width:.1f}m)"
        if not base_ceiling:
            ceiling_originally = " (originally no ceiling in the source environment)"
        else:
            by = base_ceiling.get("y", 6.0)
            bx_min = base_ceiling.get("x_min", 3.0)
            bx_max = base_ceiling.get("x_max", 5.0)
            ceiling_originally = f" (originally gap at y={by:.1f}m, x=[{bx_min:.1f}, {bx_max:.1f}] in the source environment)"
        ceiling_pattern_none = r"(- \*\*Ceiling\*\*: )None \(no vertical obstacle\)\."
        ceiling_pattern_gap = r"(- \*\*Ceiling\*\*: )Gap at y=[\d.]+m, x=\[[\d.]+, [\d.]+\] \(gap width [\d.]+m\)( \(originally [^)]+\))?\."
        if re.search(ceiling_pattern_none, description):
            description = re.sub(
                ceiling_pattern_none,
                f"\\g<1>{ceiling_new}{ceiling_originally}.",
                description,
            )
        elif re.search(ceiling_pattern_gap, description):
            description = re.sub(
                ceiling_pattern_gap,
                f"\\g<1>{ceiling_new}{ceiling_originally}.",
                description,
            )
    elif base_ceiling and not target_ceiling:
        # Target has no ceiling but base had one; keep old value per format: [new_value] (originally [old_value] in the source environment)
        by = base_ceiling.get("y", 6.0)
        bx_min = base_ceiling.get("x_min", 3.0)
        bx_max = base_ceiling.get("x_max", 5.0)
        ceiling_originally = f" (originally gap at y={by:.1f}m, x=[{bx_min:.1f}, {bx_max:.1f}] in the source environment)"
        ceiling_pattern = r"(- \*\*Ceiling\*\*: )Gap at y=[\d.]+m, x=\[[\d.]+, [\d.]+\] \(gap width [\d.]+m\)( \(originally [^)]+\))?\."
        if re.search(ceiling_pattern, description):
            description = re.sub(
                ceiling_pattern,
                f"\\g<1>None (no vertical obstacle){ceiling_originally}.",
                description,
            )

    # Joint reaction limit (max_joint_force): when finite, joints break above this force
    default_max_joint_force = float("inf")
    target_max_joint_force = target_physics_config.get("max_joint_force", default_max_joint_force)
    base_max_joint_force = base_physics_config.get("max_joint_force", default_max_joint_force)
    if target_max_joint_force != base_max_joint_force and target_max_joint_force < float("inf"):
        joint_limit_pattern = r"(- \*\*Joint reaction limit\*\*: )Structural joints do not break under reaction force in the base environment\."
        if re.search(joint_limit_pattern, description):
            description = re.sub(
                joint_limit_pattern,
                f"\\g<1>Structural joints break if reaction force exceeds {target_max_joint_force:.0f} N (originally no limit in the source environment).",
                description,
            )
        else:
            # Already has a limit (e.g. from prior stage); update numeric value and originally
            joint_limit_numeric_pattern = r"(- \*\*Joint reaction limit\*\*: Structural joints break if reaction force exceeds )(\d+\.?\d*)( N \(originally )(no limit|[^)]+)( in the source environment\)\.)"
            if re.search(joint_limit_numeric_pattern, description):
                base_str = f"{base_max_joint_force:.0f} N" if base_max_joint_force < float("inf") else "no limit"
                description = re.sub(
                    joint_limit_numeric_pattern,
                    f"\\g<1>{target_max_joint_force:.0f} N (originally {base_str} in the source environment).",
                    description,
                )

    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria to reflect visible physical changes. Format: [new_value] (originally [old_value] in the source environment)."""
    criteria = base_success_criteria
    target_y = target_terrain_config.get("target_object_y", 9.0)
    base_y = base_terrain_config.get("target_object_y", 9.0)
    target_obj = target_terrain_config.get("object", {})
    base_obj = base_terrain_config.get("object", {})
    target_mass = float(target_obj.get("mass", 20.0))
    base_mass = float(base_obj.get("mass", 20.0))
    default_sustain_s = 3.0
    default_max_structure_mass = 60.0
    target_sustain_s = float(target_terrain_config.get("min_sustain_s", default_sustain_s))
    base_sustain_s = float(base_terrain_config.get("min_sustain_s", default_sustain_s))
    target_max_mass = float(target_terrain_config.get("max_structure_mass", default_max_structure_mass))
    base_max_mass = float(base_terrain_config.get("max_structure_mass", default_max_structure_mass))

    if target_y != base_y:
        # Update "Object reaches y >= 9.0m" (lowercase "reaches" in prompt)
        pattern = r"(reaches y >= )(\d+\.?\d*)m"
        criteria = re.sub(pattern, f"\\g<1>{target_y:.1f}m (originally y >= {base_y:.1f}m in the source environment)", criteria, flags=re.IGNORECASE)

    if target_mass != base_mass:
        # Success criteria may reference object mass; if there is a "20 kg" in design constraints for object, sync it
        # Current prompt has "Mass Budget**: < 60 kg" (structure), not object. Object mass only in task_description.
        # No object mass in success_criteria text for K_05; leave criteria unchanged for mass.
        pass

    if target_sustain_s != base_sustain_s:
        # Update ">= 3.0 seconds" in success criteria
        sustain_pattern = r"(for >= )(\d+\.?\d*)( seconds \()"
        if re.search(sustain_pattern, criteria):
            criteria = re.sub(
                sustain_pattern,
                f"\\g<1>{target_sustain_s:.1f} seconds (originally {base_sustain_s:.1f} seconds in the source environment) (",
                criteria,
            )

    if target_max_mass != base_max_mass:
        # Update "Mass Budget**: < 60 kg" in success criteria
        mass_budget_pattern = r"(- \*\*Mass Budget\*\*: < )(\d+\.?\d*)( kg\.)"
        if re.search(mass_budget_pattern, criteria):
            criteria = re.sub(
                mass_budget_pattern,
                f"\\g<1>{target_max_mass:.0f} kg (originally {base_max_mass:.0f} kg in the source environment).",
                criteria,
            )

    return criteria


def get_k05_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for K-05: The Lifter task variants.
    mutation_description is for logs/orchestration only and must NOT be shown to the agent.
    """
    task_description_suffix = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Atmospheric Wind**: Constant lateral wind forces may act on all objects.
- **Narrow Clearance Obstacles**: The environment may feature ceilings with narrow gaps that restrict the lifter platform's maximum width.
- **Object Center of Mass**: The internal weight distribution of the target object may be non-uniform, causing it to tilt or slide unpredictably.
- **Joint Fragility**: Mechanical joints may have a maximum tolerance and break under excessive stress or reaction forces.
- **Surface Friction**: The object and platform surfaces may have significantly different friction from the initial specification, affecting how securely the payload is held.
- **Target Height & Object Mass**: The required lifting height and the mass of the target object may differ from the initial specification.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""
    return [
        {
            "stage_id": "Stage-1",
            "title": "Severe Hurricane Wind",
            "mutation_description": "Powerful lateral wind blows everything away.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {},
            "physics_config": {"wind_force": (400.0, 0.0)},
        },
        {
            "stage_id": "Stage-2",
            "title": "The Needle's Eye",
            "mutation_description": "Extremely narrow ceiling gap prevents wide platforms or walls.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "ceiling_gap": {"x_min": 3.4, "x_max": 4.6, "y": 5.0}
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "The Unbalanced Heavyweight",
            "mutation_description": "Heavy object with an offset center of mass.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "target_object_y": 10.5,
                "object": {"mass": 60.0, "com_offset": (0.3, 0.0)}
            },
            "physics_config": {
                "wind_force": (50.0, 0.0) 
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "The Master's Gauntlet",
            "mutation_description": "Combined wind, narrow gap, heavy load, and fragile joints.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "ceiling_gap": {"x_min": 3.2, "x_max": 4.8, "y": 6.0}, # 1.6m gap
                "target_object_y": 10.0,
                "object": {"mass": 40.0, "friction": 0.2}
            },
            "physics_config": {
                "wind_force": (150.0, 0.0),
                "max_joint_force": 1500.0
            },
        },
    ]
