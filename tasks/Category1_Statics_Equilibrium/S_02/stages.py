"""
S-02: The Skyscraper task curriculum stages (mutations).

All stage definitions live under tasks/Category1_Statics_Equilibrium/S_02.
The solver agent is NOT told the exact parameter changes; it must infer from feedback.
"""
from __future__ import annotations
from typing import Any, Dict, List
import re


def update_task_description_for_visible_changes(base_description: str, terrain_config: Dict[str, Any]) -> str:
    """
    Update task description to reflect visible physical changes (e.g., earthquake parameters, wind force).
    
    For invisible physical parameters (gravity, damping, etc.), changes are NOT reflected in description.
    """
    description = base_description
    
    # Default values
    default_earthquake_amplitude = 0.5
    default_earthquake_frequency = 2.0
    default_earthquake_start_time = 2.0
    default_wind_force = 100.0
    
    # Get current values
    earthquake_amplitude = terrain_config.get("earthquake_amplitude", default_earthquake_amplitude)
    earthquake_frequency = terrain_config.get("earthquake_frequency", default_earthquake_frequency)
    earthquake_start_time = terrain_config.get("earthquake_start_time", default_earthquake_start_time)
    wind_force = terrain_config.get("wind_force", default_wind_force)
    
    # Update earthquake parameters if changed
    if earthquake_amplitude != default_earthquake_amplitude or earthquake_frequency != default_earthquake_frequency or earthquake_start_time != default_earthquake_start_time:
        # Update "- **Earthquake**: Horizontal oscillation x(t) = 0.5 * sin(2.0 * t) starting at t=2s."
        earthquake_pattern = r"(- \*\*Earthquake\*\*: Horizontal oscillation x\(t\) = )(\d+\.?\d*)( \* sin\()(\d+\.?\d*)( \* t\) starting at t=)(\d+\.?\d*)(s\.)"
        if re.search(earthquake_pattern, description):
            amplitude_part = f"{earthquake_amplitude:.1f} (ORIGINAL: {default_earthquake_amplitude:.1f}, NOW: {earthquake_amplitude:.1f})" if earthquake_amplitude != default_earthquake_amplitude else "\\g<2>"
            frequency_part = f"{earthquake_frequency:.1f} (ORIGINAL: {default_earthquake_frequency:.1f}, NOW: {earthquake_frequency:.1f})" if earthquake_frequency != default_earthquake_frequency else "\\g<4>"
            start_time_part = f"{earthquake_start_time:.1f}s (ORIGINAL: t={default_earthquake_start_time:.1f}s, NOW: t={earthquake_start_time:.1f}s)" if earthquake_start_time != default_earthquake_start_time else "\\g<6>s"
            description = re.sub(
                earthquake_pattern,
                f"\\g<1>{amplitude_part} * sin({frequency_part} * t) starting at {start_time_part}.",
                description
            )
    
    # Update wind force if changed
    if wind_force != default_wind_force:
        # Update "- **Wind**: Constant lateral force of 100N applied to all blocks above y=20m."
        wind_pattern = r"(- \*\*Wind\*\*: Constant lateral force of )(\d+\.?\d*)N( applied to all blocks above y=20m\.)"
        if re.search(wind_pattern, description):
            description = re.sub(
                wind_pattern,
                f"\\g<1>\\g<2>N (ORIGINAL: {default_wind_force:.0f}N, NOW: {wind_force:.0f}N)\\g<3>",
                description
            )
    
    return description


def get_s02_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for S-02.

    Each stage dict fields:
      - stage_id: str
      - title: str
      - mutation_description: str (for logs, not shown to solver)
      - task_description_suffix: str (generic warning, no exact numeric changes)
      - terrain_config: dict (passed to DaVinciSandbox)
      - physics_config: dict (passed to DaVinciSandbox)
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Increased Earthquake Amplitude",
            "mutation_description": "Earthquake amplitude increased from 0.5m to 6.0m. Foundation displacement increased 12x - original design will fail.",
            "task_description_suffix": """
## Environmental Warning
The earthquake has become more violent. The ground displacement has increased dramatically.
Your structure will experience much larger foundation movements.
Stronger connections and more robust stabilization systems are essential.
""",
            "terrain_config": {
                "earthquake_amplitude": 6.0,  # Increased from 0.5m to 6.0m (original design will fail)
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Increased Wind Force",
            "mutation_description": "Wind force increased from 100N to 600N. Structural strength becomes critical - original design will fail.",
            "task_description_suffix": """
## Environmental Warning
A severe storm has arrived. Wind forces have increased dramatically.
The lateral forces acting on your structure are significantly stronger.
You may need to reinforce your structure's resistance to lateral loads.
""",
            "terrain_config": {
                "wind_force": 600.0,  # Increased from 100N to 600N (original design will fail)
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "High-Frequency Earthquake",
            "mutation_description": "Earthquake amplitude 4.0m + frequency 14.0 Hz. Higher frequency makes TMD tuning critical - original design will fail.",
            "task_description_suffix": """
## Environmental Warning
The earthquake has become more violent and rapid.
The ground displacement has increased, and the oscillation frequency has increased significantly.
Your structure will experience larger and faster foundation movements.
Stronger connections and more robust stabilization systems are essential.
Consider that the oscillation frequency has changed, which may affect tuned mass damper effectiveness.
""",
            "terrain_config": {
                "earthquake_amplitude": 5.0,  # Increased (ref passed at 4.0)
                "earthquake_frequency": 18.0,  # Higher freq (ref passed at 14.0 Hz)
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "The Perfect Storm",
            "mutation_description": "Combined challenge: frequency 18.0 Hz, amplitude 2.5m, wind 700N. Maximum difficulty - original design will fail.",
            "task_description_suffix": """
## Environmental Warning
You are facing a perfect storm of extreme conditions.
Multiple environmental factors have intensified simultaneously:
- Earthquake frequency has increased significantly
- Ground displacement has reached extreme levels
- Wind forces have become exceptionally strong

This is the ultimate test of structural engineering. Your design must be robust against all these challenges.
""",
            "terrain_config": {
                "earthquake_amplitude": 2.5,  # Increased from 0.5m to 2.5m
                "earthquake_frequency": 18.0,  # Increased from 2.0 to 18.0 Hz (original TMD tuned to 2.0 Hz will fail)
                "wind_force": 700.0,  # Increased from 100N to 700N (original design will fail)
            },
            "physics_config": {},
        },
    ]
