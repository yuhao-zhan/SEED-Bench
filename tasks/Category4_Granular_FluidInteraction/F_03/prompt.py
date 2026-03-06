"""
F-03: The Excavator task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'F_03' in _api_data and 'API_INTRO' in _api_data['F_03']:
    del _api_data['F_03']['API_INTRO']


TASK_PROMPT = {
    "task_description": """
Design an excavator arm and scoop to move granular material over an obstacle.

## Task Environment
## Task Environment
- **Material**: 200 high-friction sand particles in a pit located between x=0.0m and x=5.0m.
- **Obstacle**: A central wall at x=-1.0m. Use `has_central_wall()` to check environment state.
- **Target Hopper**: Located at x=-5.0m, y=3.0m.
- **Build Zone**: Mechanism must be built in x=[-4.0, 2.0], y=[0.0, 5.0]. Base is anchored at x=-2.0m, y=0.0m.
- **Time Limit**: Complete the task within 40 seconds.

## Task Objective
Design a mechanism that:
1. Scoops up granular material from the pit (x > 0).
2. Lifts and moves the material over the central wall (x = -1.0).
3. Deposits the material into the target hopper at x=-5.0.
...
## Success Criteria
1. **Material Transfer**: At least 15 sand particles are deposited in the hopper (x=-5.0, y=3.0).

2. **Integrity**: Mechanism remains intact throughout the operation.

## Design Constraints
- **Mass Budget**: Total structure mass <= 800 kg.
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['F_03'].values()),
}
