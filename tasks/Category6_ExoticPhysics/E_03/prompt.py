"""
E-03: The Sled task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'E_03' in _api_data and 'API_INTRO' in _api_data['E_03']:
    del _api_data['E_03']['API_INTRO']


TASK_PROMPT = {
    "task_description": """
Design a controller for a sled to navigate through a low-friction environment and pass through checkpoints.

## Task Environment
- **Sled**: A sliding body subject to thrust and minimal friction.
- **Checkpoints**: Target locations that must be reached in order.
- **Goal**: Pass through all checkpoints within the time limit.

## Task Objective
Design a control loop that:
1. Directs the sled toward the next checkpoint.
2. Manages speed and orientation to successfully pass through checkpoints.
3. Adapts to the low-friction dynamics of the environment.
""",
    "success_criteria": """
## Success Criteria
1. **Checkpoint Completion**: Sled passes through all required checkpoints.
2. **Target Reach**: Sled center enters the final target zone (x in [28, 32], y in [2.2, 2.8]).
3. **Efficiency**: Reaches the final target within the time limit.

## Design Constraints
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['E_03'].values()),
}
