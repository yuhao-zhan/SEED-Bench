"""
S-06: The Overhang task curriculum stages (mutations).
Redesigned for difficulty progression and implicit physical discovery.
"""
from __future__ import annotations
from typing import Any, Dict, List

def get_s06_curriculum_stages() -> List[Dict[str, Any]]:
    return [
        {
            "stage_id": "Stage-1",
            "title": "The Edge Restriction",
            "mutation_description": "Single Variable Change: Restricted spawn zone (x < -1.5m). Forces cantilever construction even for modest overhangs.",
            "task_description_suffix": """
## Environmental Warning
Build access near the cliff edge has been restricted. 
Your primary construction zone is now located further back from the drop-off.
You must construct an extension from this safe zone to reach the target.
""",
            "terrain_config": {
                "spawn_zone": [-10.0, -1.5],
                "target_overhang": 0.5,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "The Slick cantilever",
            "mutation_description": "Reduced friction (0.05) + Target overhang (1.2m). Baseline fails reach and stability.",
            "task_description_suffix": """
## Environmental Warning
Surface properties in this region have changed. 
Contact points feel significantly more slippery than usual.
Your structure must reach 1.2m beyond the edge while maintaining absolute static stability.
Any slight imbalance will cause the stack to drift.
""",
            "terrain_config": {
                "block_friction": 0.05,
                "table_friction": 0.05,
                "target_overhang": 1.2,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "The Low-Clearance Stretch",
            "mutation_description": "Restricted ceiling (y < 0.45m) + High reach (1.5m). Forces single-layer horizontal extension.",
            "task_description_suffix": """
## Environmental Warning
Vertical clearance is severely limited by an overhead barrier.
You cannot stack blocks vertically. The entire structure must remain within a very narrow horizontal gap.
You must reach 1.5m beyond the edge using creative horizontal weight distribution.
""",
            "terrain_config": {
                "ceiling_y": 0.45,
                "target_overhang": 1.5,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "The Seismic Abyss",
            "mutation_description": "Combined challenge: Restricted spawn (x < -1.5) + Horizontal Oscillation + Increased Gravity. Reach 0.5m.",
            "task_description_suffix": """
## Environmental Warning
Extreme environmental instability detected. 
The ground is experiencing rhythmic horizontal tremors.
Build access is restricted to the rear zone, and structural loads feel significantly heavier.
Construct a dynamically stable structure that can survive the seismic forces while reaching beyond the edge.
""",
            "terrain_config": {
                "spawn_zone": [-10.0, -1.5],
                "oscillate": True,
                "osc_amplitude": 0.1,
                "osc_frequency": 1.5,
                "target_overhang": 0.5,
                "block_friction": 0.2,
                "table_friction": 0.2,
            },
            "physics_config": {
                "gravity": (0, -25.0),
            },
        },
    ]
