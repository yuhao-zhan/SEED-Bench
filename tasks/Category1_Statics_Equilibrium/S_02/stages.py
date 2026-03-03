"""
S-02: The Skyscraper task curriculum stages (mutations).

All stage definitions live under tasks/Category1_Statics_Equilibrium/S_02.
The solver agent is NOT told the exact parameter changes; it must infer from feedback.
"""

from typing import Any, Dict, List

def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """
    Update task description to reflect visible physical changes.
    For S-02, earthquake and wind parameters are considered INVISIBLE variables
    (not explicitly numbered in the prompt), so we don't modify the base description here.
    """
    return base_description

def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    return base_success_criteria

def get_s02_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for S-02.
    Using abstract descriptions for invisible parameters as requested.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Increased Earthquake Amplitude",
            "mutation_description": "Earthquake amplitude increased significantly. Original design will fail due to larger displacement.",
            "task_description_suffix": "## Environmental Warning\nThe earthquake intensity has increased. The ground oscillations are now much larger. Structural flexibility and damping are key.",
            "terrain_config": {
                "earthquake_amplitude": 2.0, 
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Increased Wind Force",
            "mutation_description": "Wind force increased. Structure needs better lateral resistance.",
            "task_description_suffix": "## Environmental Warning\nHigh-altitude wind forces have significantly increased. Ensure your tower has enough lateral stability to avoid tipping over.",
            "terrain_config": {
                "wind_force": 400.0, 
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "High-Frequency Earthquake",
            "mutation_description": "Earthquake frequency increased significantly. Resonance tuning is critical.",
            "task_description_suffix": "## Environmental Warning\nA high-frequency earthquake has been detected. The ground vibrates much faster now. Precise TMD tuning is essential to survive the resonance.",
            "terrain_config": {
                "earthquake_amplitude": 1.0,
                "earthquake_frequency": 12.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "The Perfect Storm",
            "mutation_description": "Combined high-frequency, high-amplitude earthquake and strong wind.",
            "task_description_suffix": "## Environmental Warning\nExtreme environmental conditions: Your structure must now survive a high-frequency, high-amplitude earthquake combined with violent high-altitude wind.",
            "terrain_config": {
                "earthquake_amplitude": 1.5,
                "earthquake_frequency": 12.0,
                "wind_force": 300.0,
            },
            "physics_config": {},
        },
    ]
