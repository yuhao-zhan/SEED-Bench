"""
S-06: The Overhang task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BLOCK,
    GET_STRUCTURE_MASS,
)

TASK_PROMPT = {
    'task_description': """
Stack blocks on a table to create the longest possible overhang beyond the edge.
This task tests your ability to manage the Center of Mass and utilize friction effectively.
You cannot use joints or any form of artificial bonding. The structure must rely entirely on gravity and friction between surfaces.

## Task Environment
- **Table**: A horizontal surface extending from x=-10 to x=0. The table edge is at x=0.
- **Table Height**: The table surface is at y=0.0.
- **Surface Properties**: Both the table and the blocks provide friction, which you must utilize to stabilize the stack.
- **Block Dimensions**: width <= 4.0m, height <= 0.4m. Minimum dimension is 0.1m.
- **Spawn Rule**: All blocks must spawn with their center of mass at x < 0.0 (on the table). 
- **Block Count**: You are limited to a maximum of 20 blocks.

## Task Objective
Design a block-stacking configuration that:
1. Achieves the maximum horizontal reach (overhang) beyond the edge at x=0.
2. Remains statically stable for at least 10 seconds without tipping or collapsing.
3. Uses only friction and gravity (the `add_joint` primitive is DISABLED).

## Constraints (must satisfy)
- **Stability**: The global center of mass (COM) of the entire stack must remain over the table surface (COM x < 0). If the COM moves beyond the edge, the structure will tip.
- **No Joints**: You cannot weld or pivot blocks together.
- **Build Zone**: Blocks must be placed such that their initial centers are on the table (x < 0).
- **Clearance**: Watch out for overhead obstacles (ceilings) in some regions.
""",
    
    'success_criteria': """
## Success Criteria
1. **Static Stability**: The structure remains upright and relative motionless for at least 10 seconds.
2. **Reach**: The horizontal extent of any part of the stack exceeds the table edge (x > 0).

## Design Constraints
- **Primitive Limits**: Max block width = 4.0m, Max block height = 0.4m.
- **Block Count**: Maximum of 20 blocks.
- **Start Zone**: All initial block positions must have x < 0.
- **APIs**: Use only the primitives documented below.
""",
    
    'primitives_api': API_INTRO + ADD_BLOCK + GET_STRUCTURE_MASS,
}
