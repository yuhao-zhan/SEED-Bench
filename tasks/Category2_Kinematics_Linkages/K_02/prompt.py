"""
K-02: The Climber task Prompt and Primitives definition
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

if 'K_02' in _api_data and 'API_INTRO' in _api_data['K_02']:
    del _api_data['K_02']['API_INTRO']

task_data = _api_data['K_02']
if 'API_INTRO' in task_data:
    del task_data['API_INTRO']

TASK_PROMPT = {
    'task_description': """
Design a 2D climber mechanism that can scale a vertical wall using motor-driven segments and adhesive pads.

## Task Environment
- **Vertical Wall**: A surface on the right side of the build zone.
- **Build Zone**: x=[0, 5], y=[0, 25]. All structure components must be placed within this zone.
- **Starting Position**: Agent components should be centered around x=4.5m, y=1.5m.
- **Target**: Move the climber's torso to at least y=20.0m.

## Constraints (must satisfy)
- **Adhesion**: Use `add_pad` and `set_pad_active` to stick to the wall.
- **Motion**: The climber must maintain active upward motion for at least 10.0 seconds.
- **Mass Budget**: Total structure mass must be less than 50 kg.
- **Build Zone**: All components must stay within x=[0, 5], y=[0, 25].
- **Beam Dimensions**: 0.05 <= width, height <= 3.0 meters.

## Instructions
1. **Design**: Create a climber structure (e.g., using alternating pads and rotating legs).
2. **Control**: Use `set_motor` on pivot joints and `set_pad_active` on pads in `agent_action` to climb.
""",
    
    'success_criteria': """
## Success Criteria
1. **Vertical Movement**: Reaches y >= 20.0m.
2. **Locomotion**: Maintains active motion for >= 10.0 seconds.
3. **Stability**: Structure remains within build zone and mass limits.

## Design Constraints
- **Mass Budget**: < 50 kg.
- **APIs**: Use only the primitives documented below.
""",
    
    'primitives_api': API_INTRO + '\n\n' + '\n\n'.join(task_data.values()),
}
