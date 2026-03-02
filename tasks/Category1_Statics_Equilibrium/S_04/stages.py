"""
S-04: The Balancer task curriculum stages (mutations).

All stage definitions live under tasks/Category1_Statics_Equilibrium/S_04.
The solver agent is NOT told the exact parameter changes; it must infer from feedback.
"""

from __future__ import annotations

from typing import Any, Dict, List
import re


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """
    Update task description to reflect visible physical changes (e.g., balance time, angle limit).
    """
    description = base_description
    
    # Default values
    default_balance_time = 15.0
    default_max_angle_deviation_deg = 10.0
    
    # Get values
    target_balance_time = target_terrain_config.get("balance_time", default_balance_time)
    base_balance_time = base_terrain_config.get("balance_time", default_balance_time)
    
    target_angle = target_terrain_config.get("max_angle_deviation_deg", default_max_angle_deviation_deg)
    base_angle = base_terrain_config.get("max_angle_deviation_deg", default_max_angle_deviation_deg)
    
    # Update balance requirement in description if changed
    if target_balance_time != base_balance_time or target_angle != base_angle:
        # Update "3. Maintains a level orientation (horizontal angle within ±10 degrees) for 15 seconds. "
        balance_pattern = r"(3\. Maintains a level orientation \(horizontal angle within ±)(\d+\.?\d*)( degrees\) for )(\d+\.?\d*)( seconds\.)"
        if re.search(balance_pattern, description):
            angle_part = f"{target_angle:.0f} degrees (FROM: ±{base_angle:.0f}°, TO: ±{target_angle:.0f}°)" if target_angle != base_angle else f"{target_angle:.0f} degrees"
            time_part = f"{target_balance_time:.0f} seconds (FROM: {base_balance_time:.0f}s, TO: {target_balance_time:.0f}s)" if target_balance_time != base_balance_time else f"{target_balance_time:.0f} seconds"
            description = re.sub(
                balance_pattern,
                f"3. Maintains a level orientation (horizontal angle within ±{angle_part}) for {time_part}",
                description
            )
            
    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """
    Update success criteria to reflect visible physical changes (e.g., balance time, angle limit).
    """
    criteria = base_success_criteria
    
    # Default values
    default_balance_time = 15.0
    default_max_angle_deviation_deg = 10.0
    
    # Get values
    target_balance_time = target_terrain_config.get("balance_time", default_balance_time)
    base_balance_time = base_terrain_config.get("balance_time", default_balance_time)
    
    target_angle = target_terrain_config.get("max_angle_deviation_deg", default_max_angle_deviation_deg)
    base_angle = base_terrain_config.get("max_angle_deviation_deg", default_max_angle_deviation_deg)
    
    # Update balance criteria if changed
    if target_balance_time != base_balance_time or target_angle != base_angle:
        # Update "2. Static Balance: Maintain the main beam's angle within ±10 degrees for at least 15 seconds after the load is attached."
        balance_pattern = r"(2\. \*\*Static Balance\*\*: Maintain the main beam's angle within ±)(\d+\.?\d*)( degrees for at least )(\d+\.?\d*)( seconds)"
        if re.search(balance_pattern, criteria):
            angle_part = f"{target_angle:.0f} degrees (FROM: ±{base_angle:.0f}°, TO: ±{target_angle:.0f}°)" if target_angle != base_angle else f"{target_angle:.0f} degrees"
            time_part = f"{target_balance_time:.0f} seconds (FROM: {base_balance_time:.0f}s, TO: {target_balance_time:.0f}s)" if target_balance_time != base_balance_time else f"{target_balance_time:.0f} seconds"
            criteria = re.sub(
                balance_pattern,
                f"2. **Static Balance**: Maintain the main beam's angle within ±{angle_part} for at least {time_part}",
                criteria
            )
    
    return criteria


def get_s04_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for S-04: The Balancer task variants.
    
    Each stage dict fields:
      - stage_id: str
      - title: str
      - mutation_description: str (for logs, not shown to solver)
      - task_description_suffix: str (generic warning, no exact numeric changes)
      - terrain_config: dict (passed to Sandbox)
      - physics_config: dict (passed to Sandbox)
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Free Rotation with Increased Gravity",
            "mutation_description": "Pivot uses free rotation (revolute) + gravity -13 m/s². Requires true balance under higher gravitational forces.",
            "task_description_suffix": """
## Environmental Warning
The pivot connection uses free rotation, and physical conditions have changed.
All structures experience higher loads.
Your balancer must achieve true static equilibrium through careful mass distribution.
Consider adjusting counterweights to maintain balance.
""",
            "terrain_config": {
                "force_pivot_joint": True,  # Force revolute joint
            },
            "physics_config": {
                "gravity": (0, -13.0),  # Increased from default -10.0
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Free Rotation with Low Damping",
            "mutation_description": "Free pivot + very low angular damping (0.05). Oscillations persist much longer, requiring better passive design or active control.",
            "task_description_suffix": """
## Environmental Warning
The pivot uses free rotation, and the environment has changed.
Oscillations and vibrations persist much longer than normal.
Your balancer must achieve stable balance through careful design, as natural stabilization is minimal.
Consider implementing active stabilization or using materials with better energy dissipation.
""",
            "terrain_config": {
                "force_pivot_joint": True,
            },
            "physics_config": {
                "angular_damping": 0.05,  # Very low damping
                "linear_damping": 0.05,
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Free Rotation with High Friction",
            "mutation_description": "Free pivot + high friction (2.0) + low friction pivot surface (0.3). Friction mismatch creates stick-slip behavior.",
            "task_description_suffix": """
## Environmental Warning
The pivot uses free rotation, and contact behavior has changed significantly.
Structures may experience unexpected sliding or sticking behavior at contact points.
Your balancer must account for these contact effects in its design.
Consider how contact interactions affect the pivot contact point and overall stability.
""",
            "terrain_config": {
                "force_pivot_joint": True,
                "pivot_friction": 0.3,  # Low friction pivot (mismatch with high structure friction)
            },
            "physics_config": {
                "friction": 2.0,  # Very high friction for structures
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Extreme Physics Environment",
            "mutation_description": "Combined: free pivot + gravity -15 + very low damping (0.02) + high friction (2.5) + bouncy materials (restitution 0.4) + extended balance time (20s) + stricter angle limit (±8°).",
            "task_description_suffix": """
## Environmental Warning
Multiple physics anomalies detected simultaneously.
The pivot uses free rotation, structural loads are significantly increased, oscillations persist longer, contact behavior has changed, materials are bouncy, the balance duration requirement is extended, and the angle tolerance is stricter.
This creates an extreme engineering challenge requiring optimal balance design that accounts for all these physics changes.
Consider advanced techniques like precise mass distribution, stabilization mechanisms, and sophisticated control algorithms.
""",
            "terrain_config": {
                "force_pivot_joint": True,
                "balance_time": 20.0,  # Extended from default 15.0s
                "max_angle_deviation_deg": 8.0,  # Stricter than default 10.0°
            },
            "physics_config": {
                "gravity": (0, -15.0),  # Increased from default -10.0
                "angular_damping": 0.02,  # Extremely low damping
                "linear_damping": 0.02,
                "friction": 2.5,  # Very high friction
                "restitution": 0.4,  # Bouncy materials
            },
        },
    ]
