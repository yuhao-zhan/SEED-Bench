"""
S-06: The Overhang task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BLOCK,
    ADD_BLOCK_S06_EXTRA,
    GET_STRUCTURE_MASS,
)

TASK_PROMPT = {
    'task_description': """
Stack blocks on a table to create the longest possible overhang over the edge.
This is a test of Center of Mass management and Friction.
You cannot use joints or glue. Gravity and Friction only.

## Task Environment
- **Table**: Static surface x=[-10, 0], edge at x=0. Table top at y=1.0.
- **Friction**: Table friction = 0.5. Block-to-block friction = 0.5.
- **Block Limits**: width <= 1.0m, height <= 0.5m. Minimum 0.1m for each dimension.
- **Spawn Rule**: All blocks must spawn at x < 0 (on the table). Block center x must be < 0.
- **Block Count**: Maximum 20 blocks.
- **Stability**: The structure's center of mass (COM) must lie over the table (COM x < 0); otherwise the structure tips and the task fails.

## Task Objective
Design a block stacking structure that:
1. Creates maximum overhang beyond x=0
2. Remains stable for 10 seconds
3. Uses only friction and gravity (no joints - add_joint is DISABLED)
""",
    
    'success_criteria': """
## Success Criteria
1. **Stability**: Structure stays still for 10s. For the structure to be stable, its center of mass (COM) must remain over the table: COM x < 0. If COM x >= 0 the structure will tip and fail.
2. **Score**: Max X position of any block. Target > 0.1m.

## Design Constraints
- **No Joints**: `add_joint` is DISABLED.
- **Primitive Limit**: Maximum block width = 1.0m. Maximum block height = 0.5m. (Crucial!)
- **Start Zone**: All blocks must spawn at x < 0 (block center x < 0).
- **Block Count**: Max 20 blocks.
""",
    
    'primitives_api': API_INTRO + ADD_BLOCK + ADD_BLOCK_S06_EXTRA + GET_STRUCTURE_MASS,
}
