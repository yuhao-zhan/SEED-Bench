"""
E-01: Inverted Gravity task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'E_01' in _api_data and 'API_INTRO' in _api_data['E_01']:
    del _api_data['E_01']['API_INTRO']


TASK_PROMPT = {
    "task_description": """
Design a stable structure that stays within the boundaries of a bounded arena under time-varying gravity.

## Task Environment
- **Arena**: A bounded region with x in [0, 40] m and y in [0, 20] m. 
- **Gravity**: The gravity vector oscillates periodically between downward and upward directions (inverting gravity).
- **Obstacles**: No beam center may lie inside these obstacle zones (structure overlapping any zone causes failure): Zone 1 — x in [18.0, 22.0] m, y in [9.75, 10.25] m; Zone 2 — x in [14.0, 26.0] m, y in [12.75, 13.25] m; Zone 3 — x in [18.5, 19.5] m, y in [13.75, 14.25] m.
- **Build Zone**: Structure must be built within x=[12.0, 28.0], y=[6.0, 18.0].
- **Beam dimensions**: Each beam's width and height must be between 0.1 m and 5.0 m (enforced by the simulator).
- **Forbidden zones**: Some regions disallow beam centers; placement there causes failure. Specifically: Zone 1 — x in [19.0, 20.0] m, y in [14.5, 15.5] m; Zone 2 — x in [18.0, 21.0] m, y in [15.9, 16.1] m. Use environmental feedback to infer their locations if others are added.
- **Anchors**: You can anchor your structure to the floor, ceiling, or walls by adding joints with `body_b=None` at appropriate coordinates.
- **Joint strength**: Joints have no force limit (they do not break from overload).
- **Simulation**: The run lasts 2,500 simulation steps. Success is evaluated at the end; the structure must remain in bounds and intact for the full run.

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
- **Simulation length**: The task is evaluated over 2,500 simulation steps; you must maintain containment and integrity for the full run.
- **Mass Budget**: Total structure mass <= 200 kg.
- **Beam Limit**: Maximum 12 beams.
- **Joint strength**: Joints have no force limit (they do not break from overload).
- **Beam size**: Width and height per beam in [0.1, 5.0] m.
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['E_01'].values()),
}
