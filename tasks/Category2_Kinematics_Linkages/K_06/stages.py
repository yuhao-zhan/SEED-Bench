"""
K-06: The Wiper task curriculum stages (mutations).

All stage definitions live under tasks/Category2_Kinematics_Linkages/K_06 as requested.
The solver agent is NOT told the exact parameter changes; it must infer from feedback.
Baseline: 45 particles, seed 42, friction 0.35, 15 kg mass limit; ref agent clears 100% in ~105k steps.
Mutated stages are tuned so the reference agent fails (cannot reach 100% or cannot build).
"""

from __future__ import annotations

from typing import Any, Dict, List
import re


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description to reflect visible physical changes."""
    description = base_description
    
    # Particle count
    target_count = target_terrain_config.get("particles", {}).get("count", 45)
    base_count = base_terrain_config.get("particles", {}).get("count", 45)
    
    if target_count != base_count:
        pattern = r"(- \*\*Particles\*\*: )(\d+)( small particles)"
        description = re.sub(pattern, f"\\g<1>{target_count} small particles (originally {base_count} small particles in the source environment)", description)

    # Mass limit
    target_mass = target_terrain_config.get("max_structure_mass", 15.0)
    base_mass = base_terrain_config.get("max_structure_mass", 15.0)
    
    if target_mass != base_mass:
        pattern = r"(total mass below )(\d+\.?\d*)( kg)"
        description = re.sub(pattern, f"\\g<1>{target_mass:.2f} kg (originally {base_mass:.2f} kg in the source environment)", description)
        
    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria to reflect visible physical changes."""
    criteria = base_success_criteria
    
    # Mass limit
    target_mass = target_terrain_config.get("max_structure_mass", 15.0)
    base_mass = base_terrain_config.get("max_structure_mass", 15.0)
    
    if target_mass != base_mass:
        pattern = r"(Mass Budget\*\*: < )(\d+\.?\d*)( kg)"
        criteria = re.sub(pattern, f"\\g<1>{target_mass:.2f} kg (originally < {base_mass:.2f} kg in the source environment)", criteria)
        
    return criteria


def get_k06_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for K-06: The Wiper task variants.
    Reference agent (agent.py) must FAIL on all mutated stages.
    Each stage dict: stage_id, title, mutation_description, task_description_suffix, terrain_config, physics_config.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "More Particles and Difficult Layout",
            "mutation_description": "Particle count increased to 80 and layout seed changed. Ref agent tuned for 45 particles cannot clear all within step limit.",
            "task_description_suffix": """
## Environmental Warning
Particle distribution and load have changed in this region.
Your wiper must achieve full cleaning under the new conditions.
""",
            "terrain_config": {
                "particles": {"count": 80, "seed": 0, "friction": 0.45, "mass": 0.15},
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Stickier Particles",
            "mutation_description": "Particle friction increased from 0.35 to 0.70. Particles adhere strongly to glass; ref wiper cannot push all off.",
            "task_description_suffix": """
## Environmental Warning
Particles in this region are stickier and harder to dislodge.
Your wiper must be designed to clear them completely.
""",
            "terrain_config": {
                "particles": {"count": 45, "seed": 42, "friction": 0.70, "mass": 0.15},
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Strict Mass Limit",
            "mutation_description": "Structure mass limit reduced to 0.25 kg (ref wiper is ~0.29 kg). Ref agent build fails.",
            "task_description_suffix": """
## Environmental Warning
A strict mass budget applies. Your wiper must achieve full cleaning within the mass limit.
""",
            "terrain_config": {
                "max_structure_mass": 0.25,
                "particles": {"count": 45, "seed": 42, "friction": 0.35, "mass": 0.15},
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "Combined: More Particles, Stickier, Different Layout",
            "mutation_description": "55 particles, friction 0.55, seed 5. Ref agent cannot reach 100% in time.",
            "task_description_suffix": """
## Environmental Warning
Multiple conditions have changed: particle count, adhesion, and layout.
Your wiper must achieve full cleaning under these combined constraints.
""",
            "terrain_config": {
                "particles": {"count": 55, "seed": 5, "friction": 0.55, "mass": 0.15},
            },
            "physics_config": {},
        },
    ]
