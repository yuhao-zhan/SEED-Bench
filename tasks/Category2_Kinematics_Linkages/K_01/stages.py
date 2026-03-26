"""
K-01: The Walker task curriculum stages (mutations).

All stage definitions live under tasks/Category2_Kinematics_Linkages/K_01 as requested.
The solver agent is NOT told the exact parameter changes; it must infer from feedback.
Mutations introduce severe, physics-based difficulty: critical thresholds and
multi-variable conflicting constraints that invalidate standard solutions.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List

_DEFAULT_MAX_STRUCTURE_MASS = 100.0
_DEFAULT_GROUND_FRICTION = 0.8


def _mass_str(m: float) -> str:
    """Format mass for prompt: integer when whole, else one decimal."""
    return f"{m:.0f}" if m == int(m) else f"{m:.1f}"


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """
    Update task description to reflect visible physical changes.
    Format: [new_value] (originally [old_value] in the source environment).
    """
    description = base_description
    target_max_mass = float(target_terrain_config.get("max_structure_mass", _DEFAULT_MAX_STRUCTURE_MASS))
    base_max_mass = float(base_terrain_config.get("max_structure_mass", _DEFAULT_MAX_STRUCTURE_MASS))
    if target_max_mass != base_max_mass:
        mass_desc_pattern = re.compile(
            r"(- \*\*Mass Budget\*\*: Total structure mass must be at most )(\d+\.?\d*) kg\."
        )
        if mass_desc_pattern.search(description):
            description = mass_desc_pattern.sub(
                lambda m: f"{m.group(1)}{_mass_str(target_max_mass)} kg (originally {_mass_str(base_max_mass)} kg in the source environment).",
                description,
            )

    target_ground_friction = float(target_terrain_config.get("ground_friction", _DEFAULT_GROUND_FRICTION))
    base_ground_friction = float(base_terrain_config.get("ground_friction", _DEFAULT_GROUND_FRICTION))
    if target_ground_friction != base_ground_friction:
        friction_pattern = re.compile(
            r"(- \*\*Ground friction\*\*: Coefficient )(\d+\.?\d*)\."
        )
        if friction_pattern.search(description):
            description = friction_pattern.sub(
                lambda m: f"{m.group(1)}{target_ground_friction:.2f} (originally {base_ground_friction:.2f} in the source environment).",
                description,
            )
    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """
    Update success criteria to reflect visible physical changes.
    Format: [new_value] (originally [old_value] in the source environment).
    """
    criteria = base_success_criteria
    target_max_mass = float(target_terrain_config.get("max_structure_mass", _DEFAULT_MAX_STRUCTURE_MASS))
    base_max_mass = float(base_terrain_config.get("max_structure_mass", _DEFAULT_MAX_STRUCTURE_MASS))
    if target_max_mass != base_max_mass:
        mass_pattern = re.compile(r"(- \*\*Mass Budget\*\*: <= )(\d+\.?\d*) kg\.")
        if mass_pattern.search(criteria):
            criteria = mass_pattern.sub(
                lambda m: f"{m.group(1)}{_mass_str(target_max_mass)} kg (originally {_mass_str(base_max_mass)} kg in the source environment).",
                criteria,
            )
    return criteria


# Union of all physical variables modified across Stage-1..4 (for uniform suffix).
# Used to generate the task_description_suffix without revealing which stage has which mutation.
_UNIFORM_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Ground Friction**: The traction between the walker's contact points and the ground may differ from standard, affecting whether rolling or sliding dominates.
- **Joint Limits**: The permitted range of motion for pivot joints may differ from standard; actuation and gait behavior may be affected.
- **Gravity**: The magnitude of the gravitational field may differ from standard, changing load and stability requirements.
- **Body Friction**: The effective friction of the walker's components in contact with the ground or other bodies may differ from standard, affecting grip and slip behavior.
- **Damping**: Linear and angular damping may differ from standard, affecting how quickly mechanical energy and momentum are dissipated and whether oscillatory or sustained motion is possible.
- **Structure Mass Budget**: The maximum allowed total mass of the structure may differ from the initial environment, requiring a design that satisfies the effective limit.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint cannot rotate as expected, or how a body slips or stalls) to infer the hidden constraints and adapt your design.
"""


def get_k01_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for K-01: The Walker task variants.
    Stage-1/2: single critical variable. Stage-3/4: multi-variable, increasing difficulty.
    """
    return [
        # Stage-1: Single variable – tight mass budget (critical threshold).
        # Baseline design exceeds budget; requires a lighter or more efficient structure.
        {
            "stage_id": "Stage-1",
            "title": "Tight Structure Mass Budget",
            "mutation_description": "Max structure mass 2.8 kg. Standard walker design exceeds budget; must reduce mass or simplify structure.",
            "task_description_suffix": _UNIFORM_SUFFIX,
            "terrain_config": {"max_structure_mass": 2.8},
            "physics_config": {},
        },
        # Stage-2: ±π/6 (30°) + strong damping 2.5 so continuous rotation wastes energy and fails; requires oscillating gait.
        {
            "stage_id": "Stage-2",
            "title": "Severely Restricted Joint Limits",
            "mutation_description": "Pivot joints limited to ±π/6 (30°). Continuous rotation impossible; strong damping 2.5 requires efficient oscillating gait.",
            "task_description_suffix": _UNIFORM_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "default_joint_lower_limit": -math.pi / 6,
                "default_joint_upper_limit": math.pi / 6,
                "linear_damping": 2.5,
                "angular_damping": 2.5,
            },
        },
        # Stage-3: Lower friction + body friction cap + ±π/6 + higher damping so that with unified max_steps (350k)
        # the Initial reference solution still fails here while Stage-3 ref passes.
        {
            "stage_id": "Stage-3",
            "title": "Low Friction + Restricted Joints + Damping",
            "mutation_description": "Ground friction 0.02, max body friction 0.08, joint limits ±π/6 (30°), linear and angular damping 3.5. Balancing traction, range, and energy loss.",
            "task_description_suffix": _UNIFORM_SUFFIX,
            "terrain_config": {"ground_friction": 0.02},
            "physics_config": {
                "max_body_friction": 0.08,
                "default_joint_lower_limit": -math.pi / 6,
                "default_joint_upper_limit": math.pi / 6,
                "linear_damping": 3.5,
                "angular_damping": 3.5,
            },
        },
        # Stage-4: Extreme – reduced gravity -12, low friction, body friction cap, ±π/6 joints, damping 2.8, tight mass budget 3 kg (baseline exceeds).
        {
            "stage_id": "Stage-4",
            "title": "Extreme Challenge",
            "mutation_description": "Gravity -12, ground friction 0.02, max body friction 0.05, joint limits ±π/6 (30°), damping 2.8, max structure mass 3 kg.",
            "task_description_suffix": _UNIFORM_SUFFIX,
            "terrain_config": {"ground_friction": 0.02, "max_structure_mass": 3.0},
            "physics_config": {
                "gravity": (0, -12.0),
                "max_body_friction": 0.05,
                "default_joint_lower_limit": -math.pi / 6,
                "default_joint_upper_limit": math.pi / 6,
                "linear_damping": 2.8,
                "angular_damping": 2.8,
            },
        },
    ]
