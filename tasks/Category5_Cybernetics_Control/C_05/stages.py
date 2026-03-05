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
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Temporal sequencing windows**: Changes in the allowed time between sequential interaction phases (e.g., visiting A then B) may occur.
- **Environmental response timing**: Delays in system feedback or barrier activation may be present.
- **Interaction recovery periods**: Cooldown periods required between consecutive actions may have changed.
- **Spatial positioning requirements**: Accuracy needed in target location or relative altitude may be adjusted.
- **Repulsive field strength**: Alterations in the intensity of environmental repulsion forces may occur.
- **Repulsive field radius**: Changes in the effective reach of environmental repulsion may be present.
- **Oscillating disturbances**: Periodic external forces (e.g., wind) affecting precise control and stability may vary.
- **Regional speed limits**: Constraints on maximum velocity within specific zones may be altered.
- **Activation duration**: Time required to remain within a zone to trigger environmental changes may have changed.
- **State persistence requirements**: Changes in how long a specific state must be maintained for success may occur.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., how the sequence fails to trigger) to infer the hidden constraints and adapt your strategy.
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
