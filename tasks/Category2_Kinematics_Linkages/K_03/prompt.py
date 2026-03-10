"""
K-03: The Gripper task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO
import sys

# Add tasks directory to path to import primitives_api
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'K_03' in _api_data and 'API_INTRO' in _api_data['K_03']:
    del _api_data['K_03']['API_INTRO']

task_data = _api_data['K_03']
if 'API_INTRO' in task_data:
    del task_data['API_INTRO']

TASK_PROMPT = {
    'task_description': """
Design a robotic gripper attached to a gantry that can grasp an object on a platform and lift it vertically.

## Task Environment
- **Gantry**: A static support at y=10.0m. Use `get_anchor_for_gripper()` to anchor your base.
- **Target Object**: An object at x=5.0m, y=2.0m (on a platform at y=1.8m).
- **Target Height**: Lift the object so its center reaches at least y=3.5m.
- **Build Zone**: x=[0, 10], y=[5, 15]. The gripper base must be anchored to the gantry.

## Constraints (must satisfy)
- **Object Hold**: The object must be held above y=3.5m for at least 1.34 seconds (approx. 80 steps).
- **Mass Budget**: Total gripper structure mass must be less than 30 kg.
- **Beam Dimensions**: 0.05 <= width, height <= 2.0 meters.

## Instructions
1. **Anchor**: Weld your gripper base to the gantry anchor.
2. **Grasp**: Use motor-driven joints to design a mechanism that can securely hold the object.
3. **Lift**: Use a motor-driven joint (e.g., slider) to move the gripper vertically.
""",
    
    'success_criteria': """
## Success Criteria
1. **Vertical Lift**: Object reaches y >= 3.5m.
2. **Sustain**: Object held at target height for >= 1.34 seconds.
3. **Stability**: Object never falls below y=1.9m after being lifted.
4. **Integrity**: Gripper remains intact and within constraints.

## Design Constraints
- **Mass Budget**: < 30 kg.
- **APIs**: Use only the primitives documented below.
""",
    
    'primitives_api': API_INTRO + '\n\n' + '\n\n'.join(task_data.values()),
}
