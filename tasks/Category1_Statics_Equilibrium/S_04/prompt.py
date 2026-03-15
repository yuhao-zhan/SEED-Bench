"""
S-04: The Balancer task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'S_04' in _api_data and 'API_INTRO' in _api_data['S_04']:
    del _api_data['S_04']['API_INTRO']


TASK_PROMPT = {
    'task_description': """
Build a structure on a sharp pivot at (0, 5) that balances an asymmetric heavy load.
The goal is to design a system that maintains a level orientation despite the unbalanced weight and potential environmental disturbances.

## Task Environment
- **Pivot**: A sharp static support at (0, 5).
- **The Load**: A heavy block (mass: 200.0 kg) located at or near (3, 5.5). It may automatically attach (weld) to your structure if any part of your design is built within 0.5m of (3, 5.5), OR it may be DROPPED from above. When dropped, the load is considered caught when within 0.6 m of any part of your structure. If the load is not caught or falls, the task fails.
- **Environmental Anomalies**: The environment may contain static obstacles you must build around, or experience severe lateral wind forces that apply continuous torque to your structure.
- **Beam Dimensions**: 0.1 <= width <= 7.0 m, 0.1 <= height <= 2.0 m.

## Task Objective
Design a balanced structure that:
1. Extends to x=3.0 to successfully "catch" and support the heavy load.
2. Connects to the pivot point at (0, 5).
3. Maintains a level orientation (horizontal angle within ±10 degrees) for 15 seconds. 
4. The structure must be free to rotate about the pivot; it must rely on active or passive mass balancing, not rigid anchoring to the ground.

## Constraints (must satisfy)
- **Contact**: The structure should only touch the pivot. Any contact with the ground (y < -5.0 m) will lead to failure.
- **Pivot torque capacity** (when fragile): In environments where the pivot is fragile, the joint fails if the magnitude of static torque about the pivot exceeds 1000.0 N·m.
- **Mass Budget**: No explicit limit, but structural efficiency is key to maintaining balance.
- **Beam Limits**: Individual beams must stay within width <= 7.0m and height <= 2.0m.
""",
    
    'success_criteria': """
## Success Criteria
1. **Load Attachment**: Successfully catch or connect to the heavy load at x=3.0.
2. **Static Balance**: Maintain the main beam's angle within ±10 degrees for at least 15 seconds after the load is supported.
3. **No Grounding**: The structure does not touch the ground (y >= -5.0 m) or any surface other than the pivot.

## Design Constraints
- **Beam size**: 0.1 <= width <= 7.0 m, 0.1 <= height <= 2.0 m.
- **APIs**: Use only the primitives documented below.
""",
    
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['S_04'].values()),
}
