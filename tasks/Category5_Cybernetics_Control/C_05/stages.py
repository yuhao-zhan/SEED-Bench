"""
C-05: The Logic Lock task curriculum stages (mutations).

Mutation dimensions: trigger time window, false-trigger penalty, forces, and friction.
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
    UNIFORM_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Regional speed limits**: Constraints on the maximum velocity allowed within trigger zones to count progress.
- **Repulsive field strength**: Alterations in the intensity of forces pushing the agent away from targets.
- **Repulsive field geometry**: Changes in the direction of forces, such as the introduction of tangential or "swirling" vortex effects.
- **Input sensitivity thresholds**: Applying excessive force while inside a zone may disrupt the sensitive triggering mechanism, resetting progress.
- **Surface friction anomalies**: Significant changes in surface grip, particularly on ramps or platforms.
- **Environmental response timing**: Delays in barrier activation or system feedback after a trigger may vary.
- **Activation duration**: The required continuous time to stay within a zone to successfully trigger it.
- **Temporal sequencing windows**: Changes in the allowed time between sequential interactions (e.g., A to B).
- **State persistence requirements**: Changes in how long a previous state (like high altitude) must be maintained.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where the sequence resets or why the progress is interrupted) to infer the hidden constraints and adapt your strategy.
"""
    # Stage order: 4 mutated variants increasing difficulty
    # Baseline for reference: speed_cap: 0.5, repulsion: 22.0, recent_a_for_b: 160, trigger_stay: 25
    return [
        {
            "stage_id": "Stage-1",
            "title": "Strict Velocity Constraint",
            "mutation_description": "Reduce the allowed speed inside zones significantly, forcing precise braking.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "speed_cap_inside": 0.05,
                "recent_a_for_b": 160, # Keep baseline
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Persistent Activation Requirement",
            "mutation_description": "Significantly increase the required stay duration in target zones while under repulsion.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "trigger_stay_steps": 200,
                "repulsion_mag": 40.0,
                "recent_a_for_b": 160, # Keep baseline
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Vortex & Sensitive Trigger",
            "mutation_description": "Introduce tangential repulsion (swirling) and a force limit during triggering.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "ramp_friction": 0.05,
            },
            "physics_config": {
                "speed_cap_inside": 0.15,
                "repulsion_mag": 45.0,
                "repulsion_tangential_mag": 30.0,
                "force_limit_inside": 35.0,
                "trigger_stay_steps": 60,
                "recent_a_for_b": 140, # Slightly tighter
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Extreme Multi-Variable Chaos",
            "mutation_description": "Compound extreme physical constraints: massive swirling repulsion, low friction, and ultra-tight timing.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "ramp_friction": 0.02,
                "ground_friction": 0.2,
            },
            "physics_config": {
                "speed_cap_inside": 0.08,
                "repulsion_mag": 49.5,
                "repulsion_tangential_mag": 45.0,
                "force_limit_inside": 25.0,
                "trigger_stay_steps": 120,
                "barrier_delay_steps": 350,
                "recent_a_for_b": 120, # Even tighter
                "recent_b_for_c": 1500,
                "c_high_history": 800,
            },
        },
    ]
