"""
K-04: The Pusher task curriculum stages (mutations).

All stage definitions live under tasks/Category2_Kinematics_Linkages/K_04 as requested.
The solver agent is NOT told the exact parameter changes; it must infer from feedback.

Difficulty escalation:
- Stage-1 & 2: Single physical variable with critical threshold / non-linear effect.
- Stage-3 & 4: Multi-variable complexity; Stage-4 is the hardest.
Initial reference solution MUST fail on all four mutated environments.
"""

from __future__ import annotations

from typing import Any, Dict, List
import re

# Union of all physical variables modified across Stage-1..4 (for uniform suffix)
UNIFORM_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Center of Mass Offset**: The internal mass distribution of the pushed object may have changed, causing it to tip or rotate when pushed from certain directions.
- **Object Mass**: The weight of the payload block may be higher or lower than initial specifications, changing the force required to accelerate it.
- **Ground Friction**: The traction and slipperiness of the pushing surface may be altered.
- **Object Friction**: The friction between the payload and the ground (or pusher) may be altered.
- **Gravity**: The magnitude and direction of the gravitational force may differ from standard.
- **Linear Damping**: The rate at which the object's linear momentum is dissipated may vary.
- **Target Distance**: The required push distance may differ from the initial environment.
- **Mass Budget**: The maximum allowed total structure mass may differ from the initial environment.
- **Simulation activation**: Whether bodies may sleep during sustained contact may differ, affecting sustained motion behavior.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where the object tips, how the pusher slips, or how far the object moves) to infer the hidden constraints and adapt your design.
"""


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """
    Update task description to reflect visible physical changes.
    """
    description = base_description

    # Update Target x position (visible)
    target_dist = target_terrain_config.get("target_distance", 10.0)
    base_dist = base_terrain_config.get("target_distance", 10.0)
    if target_dist != base_dist:
        # Target line: include trailing clause in match so output is a single clean sentence
        target_pattern = r"(- \*\*Target\*\*: Push the object to at least x=)(\d+\.?\d*)(m)( \([^)]+\)\.)"
        if re.search(target_pattern, description):
            description = re.sub(
                target_pattern,
                f"\\g<1>{8.0 + target_dist:.1f}\\g<3> (originally x={8.0 + base_dist:.1f}m in the source environment).",
                description
            )
        # Distance constraint (must match Target)
        distance_pattern = r"(- \*\*Distance\*\*: The object center reaches x >= )(\d+\.?\d*)(m\.)"
        if re.search(distance_pattern, description):
            description = re.sub(
                distance_pattern,
                f"\\g<1>{8.0 + target_dist:.1f}\\g<3> (originally {8.0 + base_dist:.1f}\\g<3> in the source environment).",
                description
            )

    # Update Build Zone (if changed)
    target_bz = target_terrain_config.get("build_zone", {})
    base_bz = base_terrain_config.get("build_zone", {})
    target_x = target_bz.get("x", [0.0, 15.0])
    target_y = target_bz.get("y", [1.5, 8.0])
    base_x = base_bz.get("x", [0.0, 15.0])
    base_y = base_bz.get("y", [1.5, 8.0])
    if (target_x != base_x or target_y != base_y) and isinstance(target_x, (list, tuple)) and isinstance(target_y, (list, tuple)):
        x_min_t, x_max_t = float(target_x[0]), float(target_x[1])
        y_min_t, y_max_t = float(target_y[0]), float(target_y[1])
        x_min_b, x_max_b = float(base_x[0]), float(base_x[1])
        y_min_b, y_max_b = float(base_y[0]), float(base_y[1])
        bz_desc_pattern = r"(- \*\*Build Zone\*\*: x=\[)(\d+\.?\d*),\s*(\d+\.?\d*)(\], y=\[)(\d+\.?\d*),\s*(\d+\.?\d*)(\].)"
        if re.search(bz_desc_pattern, description):
            description = re.sub(
                bz_desc_pattern,
                lambda m: (
                    f"{m.group(1)}{x_min_t:.1f}, {x_max_t:.1f}{m.group(4)}{y_min_t:.1f}, {y_max_t:.1f}{m.group(7)} "
                    f"(originally x=[{x_min_b:.1f}, {x_max_b:.1f}], y=[{y_min_b:.1f}, {y_max_b:.1f}] in the source environment)."
                ),
                description
            )
        bz_constraint_pattern = r"(All components must stay within x=\[)(\d+\.?\d*),\s*(\d+\.?\d*)(\], y=\[)(\d+\.?\d*),\s*(\d+\.?\d*)(\].)"
        if re.search(bz_constraint_pattern, description):
            description = re.sub(
                bz_constraint_pattern,
                f"\\g<1>{x_min_t:.1f}, {x_max_t:.1f}\\g<4>{y_min_t:.1f}, {y_max_t:.1f}\\g<7> (originally x=[{x_min_b:.1f}, {x_max_b:.1f}], y=[{y_min_b:.1f}, {y_max_b:.1f}] in the source environment).",
                description
            )

    # Update Object Mass (visible: "approximately N kg" in Heavy Object line)
    target_obj = target_terrain_config.get("object", {})
    base_obj = base_terrain_config.get("object", {})
    target_obj_mass = target_obj.get("mass") if isinstance(target_obj, dict) else None
    base_obj_mass = base_obj.get("mass", 50.0) if isinstance(base_obj, dict) else 50.0
    if target_obj_mass is not None and target_obj_mass != base_obj_mass:
        # Match "1.0 m × 0.8 m (width × height), approximately N kg, at x="
        heavy_obj_pattern = r"(- \*\*Heavy Object\*\*: A rectangular block 1\.0 m × 0\.8 m \(width × height\), approximately )(\d+\.?\d*)( kg)(, at x=)"
        if re.search(heavy_obj_pattern, description):
            description = re.sub(
                heavy_obj_pattern,
                f"\\g<1>{target_obj_mass:.0f}\\g<3> (originally approximately {base_obj_mass:.0f}\\g<3> in the source environment)\\g<4>",
                description
            )

    # Update Mass Budget (if changed)
    target_mass = target_terrain_config.get("max_structure_mass", 40.0)
    base_mass = base_terrain_config.get("max_structure_mass", 40.0)
    if target_mass != base_mass:
        mass_pattern = r"(- \*\*Mass Budget\*\*: Total structure mass must be less than )(\d+\.?\d*)( kg\.)"
        if re.search(mass_pattern, description):
            description = re.sub(
                mass_pattern,
                f"\\g<1>{target_mass:.0f} kg (originally {base_mass:.0f} kg in the source environment).",
                description
            )

    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """
    Update success criteria to reflect visible physical changes.
    """
    criteria = base_success_criteria

    target_dist = target_terrain_config.get("target_distance", 10.0)
    base_dist = base_terrain_config.get("target_distance", 10.0)
    if target_dist != base_dist:
        dist_pattern = r"(\*\*Movement\*\*: Object reaches x >= )(\d+\.?\d*)(m\.)"
        if re.search(dist_pattern, criteria):
            criteria = re.sub(
                dist_pattern,
                f"\\g<1>{8.0 + target_dist:.1f}\\g<3> (originally x >= {8.0 + base_dist:.1f}\\g<3> in the source environment).",
                criteria
            )

    target_mass = target_terrain_config.get("max_structure_mass", 40.0)
    base_mass = base_terrain_config.get("max_structure_mass", 40.0)
    if target_mass != base_mass:
        # Output format: "< 26 kg (originally 40 kg in the source environment)." (no period after kg before parenthesis)
        mass_pattern = r"(\*\*Mass Budget\*\*: < )(\d+\.?\d*)( kg)(\.)"
        if re.search(mass_pattern, criteria):
            criteria = re.sub(
                mass_pattern,
                f"\\g<1>{target_mass:.0f}\\g<3> (originally {base_mass:.0f}\\g<3> in the source environment)\\g<4>",
                criteria
            )

    return criteria


def get_k04_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for K-04: The Pusher task variants.
    Designed so the initial reference solution FAILS on all four mutated environments.
    """
    return [
        # Stage-1: Single variable – critical threshold. Strict mass budget so initial ref (32 kg) fails; COM offset requires careful push-from-above design.
        {
            "stage_id": "Stage-1",
            "title": "High Tipping Hazard and Mass Limit",
            "mutation_description": "Tight mass budget and object center-of-mass offset; a heavy front-plate pusher exceeds the budget and the object tips if pushed from below.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "object": {"center_of_mass_offset": [0.2, 0.25]},
                "max_structure_mass": 26.0,
            },
            "physics_config": {"do_sleep": False},
        },
        # Stage-2: Single variable – non-linear. Very heavy object; initial pusher cannot deliver enough force.
        {
            "stage_id": "Stage-2",
            "title": "Extreme Payload Mass",
            "mutation_description": "Object mass is very high. The initial pusher structure cannot accelerate it to the target distance in time.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "object": {"mass": 95.0},
            },
            "physics_config": {"do_sleep": False},
        },
        # Stage-3: Multi-variable. Tight mass budget + slippery + high damping; initial ref exceeds mass and/or slips.
        {
            "stage_id": "Stage-3",
            "title": "Slippery Terrain, High Damping, Mass Limit",
            "mutation_description": "Tight mass budget, near-zero friction, and very high object damping. Heavy wheeled pusher exceeds budget; light designs must overcome slip and damping.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "ground_friction": 0.02,
                "object": {"friction": 0.02, "linear_damping": 4.0},
                "max_structure_mass": 26.0,
            },
            "physics_config": {"do_sleep": False},
        },
        # Stage-4: Multi-variable, hardest. Low gravity + very low friction + 14 m target + tight mass budget.
        {
            "stage_id": "Stage-4",
            "title": "Low Gravity, Low Friction, Extended Target, Mass Limit",
            "mutation_description": "Tight mass budget, weak gravity, very low friction, and 14 m push required. Initial ref exceeds mass; must use lighter design that works in low-g.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "ground_friction": 0.02,
                "object": {"friction": 0.03},
                "target_distance": 14.0,
                "max_structure_mass": 26.0,
            },
            "physics_config": {"gravity": [0, -2.0], "do_sleep": False},
        },
    ]
