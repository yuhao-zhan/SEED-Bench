"""
C-05: The Logic Lock task curriculum stages (mutations).

Mutation dimensions: trigger time window, false-trigger penalty.
All mutations use non-visible physical parameters; agent must infer from feedback.
"""

from __future__ import annotations

from typing import Any, Dict, List


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description for visible changes."""
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    return base_success_criteria


def get_c05_curriculum_stages() -> List[Dict[str, Any]]:
    """Returns ordered stage configs for C-05: The Logic Lock task variants."""
    # Stage order: base (reference) then 4 mutated variants increasing difficulty
    return [
        {
            "stage_id": "Stage-0",
            "title": "C-05 Reference",
            "mutation_description": "Reference environment (baseline).",
            "task_description_suffix": "",
            "terrain_config": {},
            "physics_config": {},
        },
        {
            "stage_id": "Stage-1",
            "title": "Tighter Temporal Window",
            "mutation_description": "Reduce the allowed 'recent A' window so B must be visited shortly after A.",
            "task_description_suffix": """
## Environmental Warning
Timing conditions in this region differ from nominal. Some temporal windows for the sequence may be more demanding.
Use feedback to infer the new timing requirements and adapt your control.
""",
            "terrain_config": {},
            "physics_config": {
                "recent_a_for_b": 40,
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Delayed Gate + Longer Cooldown",
            "mutation_description": "Barrier opens later and cooldowns are longer, increasing wait/coordination requirements.",
            "task_description_suffix": """
## Environmental Warning
Behavioral requirements for progression differ from nominal. Interaction timing with environmental elements may be altered.
Infer the new requirements from simulation feedback and adapt your strategy.
""",
            "terrain_config": {},
            "physics_config": {
                "barrier_delay_steps": 140,
                "cooldown_steps": 120,
                "recent_b_for_c": 80,
                "c_required_max_y": 3.1,
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Environmental Disturbance",
            "mutation_description": "Introduce stronger repulsion and gusting wind, and tighten allowed speed inside zones.",
            "task_description_suffix": """
## Environmental Warning
The environment exhibits stronger disturbances than nominal. Precise control and speed management are required.
Use simulation feedback to identify and adapt to these environmental dynamics.
""",
            "terrain_config": {},
            "physics_config": {
                "repulsion_mag": 40.0,
                "repulsion_range": 1.8,
                "wind_amp": 3.0,
                "wind_period": 160,
                "speed_cap_inside": 0.35,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Compound Timing & Forces",
            "mutation_description": "Combine several hidden parameter changes: longer stay requirement, narrower B→C window, stronger repulsion, and reduced high-path history window.",
            "task_description_suffix": """
## Environmental Warning
Multiple environmental and behavioral parameters have changed simultaneously. Timing, precise control, and spatial requirements differ from nominal.
You must infer the new environment from simulation feedback and ensure the sequence is completed successfully.
""",
            "terrain_config": {},
            "physics_config": {
                "trigger_stay_steps": 40,
                "recent_b_for_c": 180,
                "repulsion_mag": 45.0,
                "c_high_history": 80,
            },
        },
    ]
