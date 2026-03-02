"""
S-01: The Bridge task curriculum stages (mutations).

All stage definitions live under tasks/Category1_Statics&Equilibrium/S-01 as requested.
The solver agent is NOT told the exact parameter changes; it must infer from feedback.
"""

from __future__ import annotations

from typing import Any, Dict, List
import re


def update_task_description_for_visible_changes(base_description: str, terrain_config: Dict[str, Any]) -> str:
    """
    Update task description to reflect visible physical changes (e.g., gap width, cliff positions).
    
    For invisible physical parameters (gravity, damping, etc.), changes are NOT reflected in description.
    
    Args:
        base_description: Original task description
        terrain_config: Terrain configuration with changes
        
    Returns:
        Updated task description with visible changes explicitly marked
    """
    description = base_description
    
    # Default values
    default_gap_width = 15.0
    default_right_cliff_start = 10.0 + default_gap_width  # 25.0
    default_max_structure_mass = 2000.0
    
    # Get current values
    gap_width = terrain_config.get("gap_width", default_gap_width)
    max_structure_mass = terrain_config.get("max_structure_mass", default_max_structure_mass)
    right_cliff_start = 10.0 + gap_width
    
    # Update gap width if changed
    if gap_width != default_gap_width:
        # Update "- **Gap**: 15m wide." -> "- **Gap**: 15m wide (ORIGINAL: 15m, NOW: 18m)."
        gap_pattern = r"(- \*\*Gap\*\*: )(\d+\.?\d*)m wide\."
        if re.search(gap_pattern, description):
            description = re.sub(
                gap_pattern,
                f"\\g<1>\\g<2>m wide (ORIGINAL: {default_gap_width:.0f}m, NOW: {gap_width:.0f}m).",
                description
            )
        
        # Update "- **Right Cliff**: Starts at x=25m, y=10m." -> "- **Right Cliff**: Starts at x=25m (ORIGINAL: x=25m, NOW: x=28m), y=10m."
        right_cliff_pattern = r"(- \*\*Right Cliff\*\*: Starts at x=)(\d+\.?\d*)m"
        if re.search(right_cliff_pattern, description):
            description = re.sub(
                right_cliff_pattern,
                f"\\g<1>\\g<2>m (ORIGINAL: x={default_right_cliff_start:.0f}m, NOW: x={right_cliff_start:.0f}m)",
                description
            )
    
    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, terrain_config: Dict[str, Any]) -> str:
    """
    Update success criteria to reflect visible physical changes (e.g., max structure mass, build zone).
    
    Args:
        base_success_criteria: Original success criteria
        terrain_config: Terrain configuration with changes
        
    Returns:
        Updated success criteria with visible changes explicitly marked
    """
    criteria = base_success_criteria
    
    # Default values
    default_gap_width = 15.0
    default_right_cliff_start = 10.0 + default_gap_width  # 25.0
    default_max_structure_mass = 2000.0
    
    # Get current values
    gap_width = terrain_config.get("gap_width", default_gap_width)
    max_structure_mass = terrain_config.get("max_structure_mass", default_max_structure_mass)
    right_cliff_start = 10.0 + gap_width
    
    # Update Build Zone if gap width changed
    if gap_width != default_gap_width:
        # Update "- **Build Zone**: x=[10, 25], y=[5, 15]." -> "- **Build Zone**: x=[10, 25] (ORIGINAL: [10, 25], NOW: [10, 28]), y=[5, 15]."
        build_zone_pattern = r"(- \*\*Build Zone\*\*: x=\[10, )(\d+\.?\d*)\], y=\[5, 15\]\."
        if re.search(build_zone_pattern, criteria):
            criteria = re.sub(
                build_zone_pattern,
                f"\\g<1>\\g<2>] (ORIGINAL: [10, {default_right_cliff_start:.0f}], NOW: [10, {right_cliff_start:.0f}]), y=[5, 15].",
                criteria
            )
        
        # Update target position: "1. **Passage**: Vehicle reaches x=30m." -> "1. **Passage**: Vehicle reaches x=30m (ORIGINAL: x=30m, NOW: x=33m)."
        # target_x = right_cliff_start + 5.0
        default_target_x = default_right_cliff_start + 5.0  # 30.0
        target_x = right_cliff_start + 5.0
        target_pattern = r"(1\. \*\*Passage\*\*: Vehicle reaches x=)(\d+\.?\d*)m\."
        if re.search(target_pattern, criteria):
            criteria = re.sub(
                target_pattern,
                f"\\g<1>\\g<2>m (ORIGINAL: x={default_target_x:.0f}m, NOW: x={target_x:.0f}m).",
                criteria
            )
    
    # Update max structure mass if changed
    if max_structure_mass != default_max_structure_mass:
        # Update "- **Material Budget**: Total mass < 2000kg." -> "- **Material Budget**: Total mass < 2000kg (ORIGINAL: < 2000kg, NOW: < 1500kg)."
        mass_pattern = r"(- \*\*Material Budget\*\*: Total mass < )(\d+\.?\d*)kg\."
        if re.search(mass_pattern, criteria):
            criteria = re.sub(
                mass_pattern,
                f"\\g<1>\\g<2>kg (ORIGINAL: < {default_max_structure_mass:.0f}kg, NOW: < {max_structure_mass:.0f}kg).",
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
            "mutation_description": "Gap width increased from 15m to 18m. Bridge must span longer distance.",
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
            "mutation_description": "Gap width 18m + max structure mass reduced to 1500kg. Need efficient design.",
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
