"""
S-02: The Skyscraper task curriculum stages (mutations).

All stage definitions live under tasks/Category1_Statics_Equilibrium/S_02.
The solver agent is NOT told the exact parameter changes; it must infer from feedback.
"""
from __future__ import annotations
from typing import Any, Dict, List
import re


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """
    Update task description to reflect visible physical changes (e.g., earthquake parameters, wind force).
    
    Args:
        base_description: Original task description
        target_terrain_config: Target terrain configuration with changes
        base_terrain_config: Base terrain configuration to compare against
        
    Returns:
        Updated task description with visible changes explicitly marked
    """
    description = base_description
    
    # Default values
    default_earthquake_amplitude = 0.5
    default_earthquake_frequency = 2.0
    default_earthquake_start_time = 2.0
    default_wind_force = 100.0
    
    # Get values
    target_amplitude = target_terrain_config.get("earthquake_amplitude", default_earthquake_amplitude)
    base_amplitude = base_terrain_config.get("earthquake_amplitude", default_earthquake_amplitude)
    
    target_frequency = target_terrain_config.get("earthquake_frequency", default_earthquake_frequency)
    base_frequency = base_terrain_config.get("earthquake_frequency", default_earthquake_frequency)
    
    target_start_time = target_terrain_config.get("earthquake_start_time", default_earthquake_start_time)
    base_start_time = base_terrain_config.get("earthquake_start_time", default_earthquake_start_time)
    
    target_wind = target_terrain_config.get("wind_force", default_wind_force)
    base_wind = base_terrain_config.get("wind_force", default_wind_force)
    
    # Update earthquake parameters if changed
    if target_amplitude != base_amplitude or target_frequency != base_frequency or target_start_time != base_start_time:
        # Update "- **Earthquake**: Horizontal oscillation x(t) = 0.5 * sin(2.0 * t) starting at t=2s."
        earthquake_pattern = r"(- \*\*Earthquake\*\*: Horizontal oscillation x\(t\) = )(\d+\.?\d*)( \* sin\()(\d+\.?\d*)( \* t\) starting at t=)(\d+\.?\d*)(s\.)"
        if re.search(earthquake_pattern, description):
            amplitude_part = f"{target_amplitude:.1f} (FROM: {base_amplitude:.1f}, TO: {target_amplitude:.1f})" if target_amplitude != base_amplitude else "\\g<2>"
            frequency_part = f"{target_frequency:.1f} (FROM: {base_frequency:.1f}, TO: {target_frequency:.1f})" if target_frequency != base_frequency else "\\g<4>"
            start_time_part = f"{target_start_time:.1f}s (FROM: t={base_start_time:.1f}s, TO: t={target_start_time:.1f}s)" if target_start_time != base_start_time else "\\g<6>s"
            description = re.sub(
                earthquake_pattern,
                f"\\g<1>{amplitude_part} * sin({frequency_part} * t) starting at {start_time_part}.",
                description
            )
    
    # Update wind force if changed
    if target_wind != base_wind:
        # Update "- **Wind**: Constant lateral force of 100N applied to all blocks above y=20m."
        wind_pattern = r"(- \*\*Wind\*\*: Constant lateral force of )(\d+\.?\d*)N( applied to all blocks above y=20m\.)"
        if re.search(wind_pattern, description):
            description = re.sub(
                wind_pattern,
                f"\\g<1>\\g<2>N (FROM: {base_wind:.0f}N, TO: {target_wind:.0f}N)\\g<3>",
                description
            )
    
    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    return base_success_criteria


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
