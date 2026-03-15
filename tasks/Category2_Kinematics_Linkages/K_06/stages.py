"""
K-06: The Wiper task curriculum stages (mutations).

All stage definitions live under tasks/Category2_Kinematics_Linkages/K_06 as requested.
The solver agent is NOT told the exact parameter changes; it must infer from feedback.
Mutations introduce essential, physics-based difficulty (critical thresholds, torque limits, mass budget).
"""

from __future__ import annotations

from typing import Any, Dict, List
import re


def _get_uniform_task_description_suffix() -> str:
    """
    Build suffix from the UNION of all physical variables modified across Stage-1 to Stage-4.
    Agent must discover which specific conditions apply via trial and feedback.
    """
    return """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Particle Count**: The total number of particles requiring removal may be adjusted.
- **Particle Distribution**: The initial layout and seeding of particles on the surface may have changed.
- **Particle Friction**: The adhesion and resistance of particles to being moved may be altered.
- **Particle Mass**: The mass and inertia of the individual particles may differ from standard.
- **Mass Budget**: The maximum total mass allowed for the wiper structure may be adjusted.
- **Motor Torque Limit**: The maximum torque available at motor-driven joints may be capped in this region, limiting the force the mechanism can apply.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description to reflect visible physical changes."""
    description = base_description

    # Particle count
    target_count = target_terrain_config.get("particles", {}).get("count", 45)
    base_count = base_terrain_config.get("particles", {}).get("count", 45)

    if target_count != base_count:
        pattern = r"(- \*\*Particles\*\*: )(\d+)( small particles)"
        description = re.sub(pattern, f"\\g<1>{target_count} small particles (originally {base_count} small particles in the source environment)", description)

    # Mass limit
    target_mass = target_terrain_config.get("max_structure_mass", 15.0)
    base_mass = base_terrain_config.get("max_structure_mass", 15.0)

    if target_mass != base_mass:
        pattern = r"(Total structure mass must be less than )(\d+\.?\d*)( kg)"
        description = re.sub(pattern, f"\\g<1>{target_mass:.2f} kg (originally {base_mass:.2f} kg in the source environment)", description)

    # Motor torque cap (when set by mutation; base has no cap)
    target_motor_cap = target_terrain_config.get("max_motor_torque")
    base_motor_cap = base_terrain_config.get("max_motor_torque")
    if target_motor_cap is not None:
        old_val = f"{base_motor_cap:.1f} N·m" if base_motor_cap is not None else "no cap"
        pattern = r"(- \*\*Motor torque\*\*: )No environment cap \(solver may request up to API limits\)\."
        replacement = f"\\g<1>Capped at {target_motor_cap:.1f} N·m (originally {old_val} in the source environment)."
        if re.search(pattern, description):
            description = re.sub(pattern, replacement, description)

    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria to reflect visible physical changes."""
    criteria = base_success_criteria

    # Mass limit
    target_mass = target_terrain_config.get("max_structure_mass", 15.0)
    base_mass = base_terrain_config.get("max_structure_mass", 15.0)

    if target_mass != base_mass:
        pattern = r"(\*\*Mass Budget\*\*: < )(\d+\.?\d*)( kg)"
        criteria = re.sub(pattern, f"\\g<1>{target_mass:.2f} kg (originally < {base_mass:.2f} kg in the source environment)", criteria)

    return criteria


def get_k06_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for K-06: The Wiper task variants.
    Stage-1 & 2: Single-variable critical thresholds (heavy particles; motor torque cap).
    Stage-3 & 4: Multi-variable, conflicting constraints; difficulty increases.
    """
    UNIFORM_SUFFIX = _get_uniform_task_description_suffix()

    return [
        {
            "stage_id": "Stage-1",
            "title": "Heavy Particles (Critical Mass Threshold)",
            "mutation_description": "Particle mass 1.5 kg each; motor torque capped at 135 N·m. Standard wiper cannot deliver enough impulse to clear 80%.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "max_motor_torque": 135.0,
                "particles": {"count": 45, "seed": 42, "friction": 0.35, "mass": 1.5},
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Motor Torque Limit and Sticky Particles",
            "mutation_description": "Max motor torque capped at 50 N·m; particle friction 0.65. Standard high-torque wiper is neutered.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "max_motor_torque": 50.0,
                "particles": {"count": 45, "seed": 42, "friction": 0.65, "mass": 0.15},
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Strict Mass Budget and Higher Particle Load",
            "mutation_description": "Structure mass limit 0.25 kg; 60 particles. Reference solution exceeds mass and cannot be built legally.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "max_structure_mass": 0.25,
                "particles": {"count": 60, "seed": 7, "friction": 0.35, "mass": 0.15},
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "Combined: Ultra-Light Budget, Torque Cap, Heavy Sticky Particles",
            "mutation_description": "Mass 0.2 kg, motor cap 200 N·m, 50 particles, friction 0.6, particle mass 0.5. Conflicting constraints.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "max_structure_mass": 0.2,
                "max_motor_torque": 200.0,
                "particles": {"count": 50, "seed": 5, "friction": 0.6, "mass": 0.5},
            },
            "physics_config": {},
        },
    ]
