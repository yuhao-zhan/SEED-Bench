"""
C-05: The Logic Lock task curriculum stages (mutations).

TODO: For later mutated tasks, define stages here.
Mutation dimensions: trigger time window, false-trigger penalty.
"""

from __future__ import annotations

from typing import Any, Dict, List


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
            "task_description_suffix": "\n## Environmental Warning\nTiming constraints are stricter in this stage; sequence windows are tighter.\n",
            "terrain_config": {},
            "physics_config": {
                # Reduce the allowed time between A and B (hidden timing parameter)
                "recent_a_for_b": 40,
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Delayed Gate + Longer Cooldown",
            "mutation_description": "Barrier opens later and cooldowns are longer, increasing wait/coordination requirements.",
            "task_description_suffix": "\n## Environmental Warning\nBarriers and timing behavior are altered; expect longer waits when interacting with the gate.\n",
            "terrain_config": {},
            "physics_config": {
                "barrier_delay_steps": 140,
                "cooldown_steps": 120,
                # Narrow the allowed B->C recent window and raise the high-path threshold
                "recent_b_for_c": 80,
                "c_required_max_y": 3.1,
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Environmental Disturbance",
            "mutation_description": "Introduce stronger repulsion and gusting wind, and tighten allowed speed inside zones.",
            "task_description_suffix": "\n## Environmental Warning\nThe environment has stronger hidden disturbances (wind/repulsion). Maintain controlled low-speed entries.\n",
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
            "task_description_suffix": "\n## Environmental Warning\nMultiple hidden dynamics changed simultaneously — timing and precise control are critical.\n",
            "terrain_config": {},
            "physics_config": {
                "trigger_stay_steps": 40,
                "recent_b_for_c": 180,
                "repulsion_mag": 45.0,
                "c_high_history": 80,
            },
        },
    ]
