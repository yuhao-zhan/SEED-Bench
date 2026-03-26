"""
S-06: The Overhang task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'S_06' in _api_data and 'API_INTRO' in _api_data['S_06']:
    del _api_data['S_06']['API_INTRO']


TASK_PROMPT = {
    'task_description': """
Stack blocks on a table to create the longest possible overhang beyond the edge.
This task tests your ability to manage the Center of Mass and utilize friction effectively.
You cannot use joints or any form of artificial bonding. The structure must rely entirely on gravity and friction between surfaces.

## Task Environment
- **Table**: A horizontal surface extending from x=-20 to x=0. The table edge is at x=0.
- **Table Height**: The table surface is at y=0.0.
- **Surface Properties**: Both the table and the blocks provide friction, which you must utilize to stabilize the stack.
- **Goal**: Reach x >= 0.1m beyond the edge.
- **Block Dimensions**: width <= 1.0m, height <= 0.2m.
- **Spawn Rule**: Blocks must be initialized within the permitted build access zone: x in [-10.0, 0.0].
- **Build Access Zone**: The x-interval for block placement is constrained; check stage requirements.
- **Block Count**: You are limited to a maximum of 100 blocks.
- **Block Density**: The default density for all blocks is 1.0 units per square meter.
- **Mass Budget**: Total structure mass must be less than or equal to 20000.0 units.
- **Stability Requirement**: The structure must remain static for at least 10.0 seconds to be considered stable.
- **Support Boundary**: If any part of the structure falls below y = -5.0 m, the structure is considered to have left the support and the task fails.
- **Clearance**: Watch out for overhead obstacles (ceilings) in some regions. Current clearance y: 100.0m.
""",
    
    'success_criteria': """
## Success Criteria
1. **Static Stability**: The structure remains upright and relatively motionless for at least 10 seconds.
2. **Reach**: The horizontal extent of any part of the stack exceeds the table edge (Tip reaches x >= 0.1m).

## Design Constraints
- **Primitive Limits**: Max block width = 1.0m, Max block height = 0.2m.
- **Block Count**: Maximum of 100 blocks.
- **Mass Budget**: Total mass must be <= 20000.0 units.
- **Start Zone**: All initial block positions must be within the designated build access zone on the table.
- **APIs**: Use only the primitives documented below.
""",
    
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['S_06'].values()),
}
