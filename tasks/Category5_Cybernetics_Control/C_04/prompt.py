"""
C-04: The Escaper task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'C_04' in _api_data and 'API_INTRO' in _api_data['C_04']:
    del _api_data['C_04']['API_INTRO']


TASK_PROMPT = {
    "task_description": """
Design a controller for a whisker-equipped robot to unlock and escape a narrow maze.

## Task Environment
- **Agent**: A small robot with three whisker sensors (front, left, right).
- **Passage**: A winding path with walls.
- **Goal**: Reach the exit zone at the end of the passage.
- **Unlock Condition**: The exit is initially locked. To unlock it, the agent must perform a specific behavioral sequence: stay within the activation zone (x in [6.0, 8.0] m) and move backward at a very low speed for a sustained period (discover exact thresholds via feedback).
- **Exit Zone**: Located at x >= 18.0m, y in [1.25, 1.45] m. Once reached, the agent must hold its position there for a minimum duration.

## Task Objective
Design a control loop that:
1. Uses whisker sensor readings to navigate the winding passage.
2. Identifies the activation zone (x in [6.0, 8.0] m) and performs the required "unlock" behavior.
3. Reaches the exit zone and maintains its position for at least 60 consecutive steps to complete the escape.
""",
    "success_criteria": """
## Success Criteria
1. **Unlock & Reach**: Successfully unlock the exit and reach the zone (x >= 18.0m, y in [1.25, 1.45] m).
2. **Hold**: Maintain position in the exit zone for at least 60 consecutive steps.
3. **Survival**: No sustained collisions or getting stuck.

## Design Constraints
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['C_04'].values()),
}
