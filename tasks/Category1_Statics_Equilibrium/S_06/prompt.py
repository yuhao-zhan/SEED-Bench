"""
S-06: The Overhang task Prompt and Primitives definition
"""

import json
import os

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)


TASK_PROMPT = {
    'task_description': """
Stack blocks on a table to create the longest possible overhang beyond the edge.
This task tests your ability to manage the Center of Mass and utilize friction effectively.
You cannot use joints or any form of artificial bonding. The structure must rely entirely on gravity and friction between surfaces.

## Task Environment
- **Table**: A horizontal surface extending from x=-10 to x=0. The table edge is at x=0.
- **Table Height**: The table surface is at y=0.0.
- **Surface Properties**: Both the table and the blocks provide friction, which you must utilize to stabilize the stack.
- **Goal**: Reach x >= 0.1m beyond the edge.
- **Block Dimensions**: width <= 4.0m, height <= 0.4m. Minimum dimension is 0.1m.
- **Spawn Rule**: Blocks must be initialized within the permitted build access zone (typically x < 0.0, but may be further restricted: x in [-10.0, 0.0]).
- **Block Count**: You are limited to a maximum of 20 blocks.
- **Clearance**: Watch out for overhead obstacles (ceilings) in some regions. Current clearance y: 100.0m.
""",
    
    'success_criteria': """
## Success Criteria
1. **Static Stability**: The structure remains upright and relatively motionless for at least 10 seconds.
2. **Reach**: The horizontal extent of any part of the stack exceeds the table edge (Tip reaches x > 0.1m).

## Design Constraints
- **Primitive Limits**: Max block width = 4.0m, Max block height = 0.4m.
- **Block Count**: Maximum of 20 blocks.
- **Start Zone**: All initial block positions must be within the designated build access zone on the table.
- **APIs**: Use only the primitives documented below.
""",
    
    'primitives_api': '\n\n'.join(_api_data['S_06'].values()),
}
