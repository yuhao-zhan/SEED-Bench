"""
E-01: Inverted Gravity task Prompt and Primitives definition
"""

import json
import os

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)


TASK_PROMPT = {
    "task_description": """
Design a stable structure that stays within the boundaries of a bounded arena under time-varying gravity.

## Task Environment
- **Arena**: A bounded region with x in [0, 40] m and y in [0, 20] m. 
- **Gravity**: The gravity vector oscillates periodically between downward and upward directions (inverting gravity).
- **Obstacles**: Several horizontal bars are fixed within the arena.
- **Build Zone**: Structure must be built within x=[12.0, 28.0], y=[6.0, 18.0]. 
- **Anchors**: You can anchor your structure to the floor, ceiling, or walls by adding joints with `body_b=None` at appropriate coordinates.

## Task Objective
Design a structure that:
1. Remains entirely within the arena boundaries throughout the simulation despite gravity inversions.
2. Avoids overlapping with the fixed obstacles.
3. Maintains structural integrity (joints must not break under the alternating loads).
""",
    "success_criteria": """
## Success Criteria
1. **Containment**: No part of the structure (or any dynamic bodies) leaves the arena bounds.
2. **Integrity**: The structure remains intact; no joints are broken.

## Design Constraints
- **Mass Budget**: Total structure mass <= 200 kg.
- **Beam Limit**: Maximum 12 beams.
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': '\n\n'.join(_api_data['E_01'].values()),
}
