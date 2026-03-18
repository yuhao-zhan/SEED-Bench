from __future__ import annotations
import re
from typing import Any, Dict, List

_DEFAULT_MAGNETS = [
    (12.0, 4.0, -300.0), (12.0, 5.0, -300.0), (12.0, 6.0, -300.0),
    (12.0, 7.0, -300.0), (12.0, 8.0, -280.0), (12.0, 8.3, -260.0),
    (11.0, 9.7, -200.0), (13.0, 9.7, -200.0), (15.0, 9.7, -200.0),
    (17.0, 9.7, -200.0), (19.0, 9.7, -200.0), (21.0, 9.7, -180.0),
    (15.0, 9.0, -250.0, 230.0, 0.12), (20.0, 9.0, -350.0, 330.0, 0.15, 3.14159),
    (19.0, 3.0, 160.0), (21.0, 3.5, 130.0),
    (24.0, 5.0, -190.0), (24.0, 8.2, -180.0),
    (24.0, 6.6, -180.0, 160.0, 0.165),
    (26.0, 5.5, -130.0), (27.0, 9.5, -120.0), (29.5, 7.5, 95.0),
]

def _magnets_stage1() -> List[tuple]:
    """Stage 1: The Great Wall. A single massive wall blocks the direct path."""
    return [(14.0, y, -800.0) for y in range(0, 15)]

def _magnets_stage2() -> List[tuple]:
    return [tuple(x) for x in _DEFAULT_MAGNETS]

def _magnets_stage3() -> List[tuple]:
    return [tuple(x) for x in _DEFAULT_MAGNETS]

def _magnets_stage4() -> List[tuple]:
    return [tuple(x) for x in _DEFAULT_MAGNETS]

UNIFORM_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Electromagnetic Fields**: The spatial layout and strength of repulsive walls or attractive nodes may differ from the source environment.
- **Gravity**: The magnitude and direction of the gravitational field may differ from the source environment.
- **Motion Damping**: Environmental friction and air resistance may differ from the source environment.
- **Maximum Thrust**: The engine's power limit may differ from the source environment.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where the body gets stuck or how it responds to thrust) to infer the hidden constraints and adapt your design.
"""

_DEFAULT_MAX_THRUST = 165.0


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description with visible changes using format: [new_value] (originally [old_value] in the source environment)."""
    description = base_description
    target_terrain_config = target_terrain_config or {}
    base_terrain_config = base_terrain_config or {}
    target_max_thrust = float(target_terrain_config.get("max_thrust", _DEFAULT_MAX_THRUST))
    base_max_thrust = float(base_terrain_config.get("max_thrust", _DEFAULT_MAX_THRUST))
    if target_max_thrust != base_max_thrust:
        # Update "capped at X" in task description
        thrust_cap_pattern = r"(- \*\*Maximum Thrust\*\*: The thrust vector magnitude is capped at )(\d+\.?\d*)( \(engine limit\)\.)"
        if re.search(thrust_cap_pattern, description):
            description = re.sub(
                thrust_cap_pattern,
                lambda m: f"{m.group(1)}{target_max_thrust:.1f} (originally {base_max_thrust:.1f} in the source environment){m.group(3)}",
                description,
            )
    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria with visible changes using format: [new_value] (originally [old_value] in the source environment)."""
    criteria = base_success_criteria
    target_terrain_config = target_terrain_config or {}
    base_terrain_config = base_terrain_config or {}
    target_max_thrust = float(target_terrain_config.get("max_thrust", _DEFAULT_MAX_THRUST))
    base_max_thrust = float(base_terrain_config.get("max_thrust", _DEFAULT_MAX_THRUST))
    if target_max_thrust != base_max_thrust:
        thrust_constraint_pattern = r"(- \*\*Maximum Thrust\*\*: Thrust magnitude must not exceed )(\d+\.?\d*)(\.)"
        if re.search(thrust_constraint_pattern, criteria):
            criteria = re.sub(
                thrust_constraint_pattern,
                lambda m: f"{m.group(1)}{target_max_thrust:.1f} (originally {base_max_thrust:.1f} in the source environment){m.group(3)}",
                criteria,
            )
    return criteria

def get_e05_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for E-05: The Magnet task variants.
    Information Hiding: Uniform suffix for all stages to test physical reasoning.
    mutation_description is for logs/orchestration only and must NOT be shown to the agent.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "The Great Wall",
            "mutation_description": "Electromagnetic layout completely replaced by a massive vertical repulsive wall. Normal corridor strategy hits a dead end.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "magnets": _magnets_stage1(),
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Updraft",
            "mutation_description": "Gravity is inverted (pulls upwards). Agent must thrust downwards to avoid floating into the pit ceiling or over the target.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "magnets": _magnets_stage2(),
            },
            "physics_config": {
                "gravity": (0, 5.0),
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Viscous Abyss",
            "mutation_description": "Heavy gravity combined with extreme linear damping and increased thrust capacity. Agent must maintain sustained maximum power output.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "magnets": _magnets_stage3(),
                "max_thrust": 500.0,
            },
            "physics_config": {
                "gravity": (0, -15.0),
                "linear_damping": 2.0,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Crushing Weight",
            "mutation_description": "Extreme crushing gravity requires near-maximum vertical thrust just to hover, leaving little lateral thrust available.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "magnets": _magnets_stage4(),
                "max_thrust": 500.0,
            },
            "physics_config": {
                "gravity": (0, -25.0),
            },
        },
    ]