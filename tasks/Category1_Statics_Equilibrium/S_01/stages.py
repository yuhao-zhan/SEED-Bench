"""
S-01: The Bridge task curriculum stages (mutations).

All stage definitions live under tasks/Category1_Statics&Equilibrium/S-01 as requested.
The solver agent is NOT told the exact parameter changes; it must infer from feedback.
"""

from __future__ import annotations

from typing import Any, Dict, List
import re


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """
    Update task description to reflect visible physical changes (e.g., gap width, cliff positions).
    
    Args:
        base_description: Original task description
        target_terrain_config: Target terrain configuration with changes
        base_terrain_config: Base terrain configuration to compare against
        
    Returns:
        Updated task description with visible changes explicitly marked
    """
    description = base_description
    
    # Default values
    default_gap_width = 15.0
    
    # Get values
    target_gap_width = target_terrain_config.get("gap_width", default_gap_width)
    base_gap_width = base_terrain_config.get("gap_width", default_gap_width)
    
    target_right_cliff_start = 10.0 + target_gap_width
    base_right_cliff_start = 10.0 + base_gap_width
    
    # Update gap width if changed
    if target_gap_width != base_gap_width:
        # The prompt doesn't have a direct "Gap: 15m wide" line, it's inferred from cliffs.
        # But we can add a note or replace the right cliff start.
        
        # Update "- **Right Cliff**: use new env value, note original in source env (keep trailing ", y=10.0m." if present)
        right_cliff_pattern = r"(- \*\*Right Cliff\*\*: Starts at x=)(\d+\.?\d*)m(, y=[\d.]+m\.)?"
        if re.search(right_cliff_pattern, description):
            description = re.sub(
                right_cliff_pattern,
                lambda m: f"{m.group(1)}{target_right_cliff_start:.1f}m (originally x={base_right_cliff_start:.1f}m in the source environment){m.group(3) if m.group(3) else '.'}",
                description
            )
    
    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """
    Update success criteria to reflect visible physical changes (e.g., max structure mass, build zone).
    
    Args:
        base_success_criteria: Original success criteria
        target_terrain_config: Target terrain configuration with changes
        base_terrain_config: Base terrain configuration to compare against
        
    Returns:
        Updated success criteria with visible changes explicitly marked
    """
    # Note: Build Zone info is actually in task_description, but we keep the logic here for consistency
    # and also update success_criteria if it contained any such info.
    criteria = base_success_criteria
    
    # Default values
    default_gap_width = 15.0
    default_max_structure_mass = 2000.0
    
    # Get values
    target_gap_width = target_terrain_config.get("gap_width", default_gap_width)
    base_gap_width = base_terrain_config.get("gap_width", default_gap_width)
    
    target_right_cliff_start = 10.0 + target_gap_width
    base_right_cliff_start = 10.0 + base_gap_width
    
    target_max_mass = target_terrain_config.get("max_structure_mass", default_max_structure_mass)
    base_max_mass = base_terrain_config.get("max_structure_mass", default_max_structure_mass)
    
    # Update target position: use new env value in main text, note original in source env
    if target_gap_width != base_gap_width:
        base_target_x = base_right_cliff_start + 5.0
        target_x = target_right_cliff_start + 5.0
        target_pattern = r"(1\. \*\*Passage\*\*: Vehicle reaches x >= )(\d+\.?\d*)m\."
        if re.search(target_pattern, criteria):
            criteria = re.sub(
                target_pattern,
                f"\\g<1>{target_x:.1f}m (originally x >= {base_target_x:.1f}m in the source environment).",
                criteria
            )
    
    # Update max structure mass: use new env value in main text, note original in source env
    if target_max_mass != base_max_mass:
        mass_pattern = r"(- \*\*Mass Budget\*\*: < )(\d+\.?\d*) kg\."
        if re.search(mass_pattern, criteria):
            criteria = re.sub(
                mass_pattern,
                f"\\g<1>{target_max_mass:.0f} kg (originally < {base_max_mass:.0f} kg in the source environment).",
                criteria
            )
    
    return criteria


def get_s01_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for S-01: The Bridge task variants.
    
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
            "title": "Wider Gap",
            "mutation_description": "Gap width increased from 15m to 21m. Bridge must span longer distance.",
            "task_description_suffix": """
## Environmental Warning
The gap between the cliffs has widened.
Your bridge must span a longer distance to connect the two sides.
Consider using truss designs or additional supports to maintain structural integrity.
""",
            "terrain_config": {
                "gap_width": 21.0,  # Increased from default 15.0m (was 18, ref passed)
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Heavy Gravity",
            "mutation_description": "Gravity increased from -10 to -15 m/s². Structures experience higher loads.",
            "task_description_suffix": """
## Environmental Warning
Physical conditions in this region have changed.
All structures experience significantly increased loads.
Your bridge must be designed to withstand higher structural stresses.
""",
            "terrain_config": {},
            "physics_config": {
                "gravity": (0, -15.0),  # Increased from default -10.0
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Wider Gap and Lightweight Constraint",
            "mutation_description": "Gap width 21m + max structure mass reduced to 950kg. Need efficient design.",
            "task_description_suffix": """
## Environmental Warning
The gap has widened, and material resources are limited.
Your bridge must span a longer distance while using less material.
Efficient structural designs such as trusses or arches may be necessary.
""",
            "terrain_config": {
                "gap_width": 21.0,  # Increased from default 15.0m
                "max_structure_mass": 950.0,  # Reduced (ref passed at 1100)
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "Extreme Challenge",
            "mutation_description": "Gap width 20m + gravity -15 + max structure mass 1200kg. Maximum difficulty.",
            "task_description_suffix": """
## Environmental Warning
Multiple environmental anomalies detected simultaneously.
The gap is extremely wide, structural loads are significantly increased, and material resources are severely limited.
This is an extreme engineering challenge requiring optimal structural design.
Consider advanced techniques like trusses, arches, or cantilever designs.
""",
            "terrain_config": {
                "gap_width": 20.0,  # Increased from default 15.0m
                "max_structure_mass": 1200.0,  # Reduced from default 2000.0kg
            },
            "physics_config": {
                "gravity": (0, -15.0),  # Increased from default -10.0
            },
        },
    ]
