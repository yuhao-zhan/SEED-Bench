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
    task_description_suffix = """
Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - recent_a_for_b: Changes in the timing window allowed between sequential actions A and B.
 - barrier_delay_steps: Unexpected delays in environmental responses to trigger activations.
 - cooldown_steps: Increased waiting periods required between consecutive interactions.
 - recent_b_for_c: Tighter temporal constraints on the final sequence completion.
 - c_required_max_y: Stricter spatial positioning requirements for target activation.
 - repulsion_mag: Alterations in the strength of repulsive force fields.
 - repulsion_range: Changes in the effective radius of environmental repulsion.
 - wind_amp / wind_period: Oscillating environmental forces affecting precise control.
 - speed_cap_inside: Stricter limits on the maximum allowed speed within specific zones.
 - trigger_stay_steps: Increased duration required to remain within a zone to activate it.
 - c_high_history: Changes in the requirement for sustained state history to achieve success.

Discovery via feedback: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""
    # Stage order: base (reference) then 4 mutated variants increasing difficulty
    return [
        {
            "stage_id": "Stage-0",
            "title": "C-05 Reference",
            "mutation_description": "Reference environment (baseline).",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {},
            "physics_config": {},
        },
        {
            "stage_id": "Stage-1",
            "title": "Tighter Temporal Window",
            "mutation_description": "Reduce the allowed 'recent A' window so B must be visited shortly after A.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {},
            "physics_config": {
                "recent_a_for_b": 40,
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Delayed Gate + Longer Cooldown",
            "mutation_description": "Barrier opens later and cooldowns are longer, increasing wait/coordination requirements.",
            "task_description_suffix": task_description_suffix,
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
            "task_description_suffix": task_description_suffix,
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
            "task_description_suffix": task_description_suffix,
            "terrain_config": {},
            "physics_config": {
                "trigger_stay_steps": 40,
                "recent_b_for_c": 180,
                "repulsion_mag": 45.0,
                "c_high_history": 80,
            },
        },
    ]
