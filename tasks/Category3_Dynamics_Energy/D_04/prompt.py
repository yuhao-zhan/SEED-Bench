"""
D-04: The Swing task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'D_04' in _api_data and 'API_INTRO' in _api_data['D_04']:
    del _api_data['D_04']['API_INTRO']


TASK_PROMPT = {
    "task_description": """
Design a control strategy to pump a swing seat to reach a target zone.

## Task Environment
- **Swing Seat**: A heavy body attached to a fixed pivot at (10, 10) m.
- **Wind**: Environmental wind forces may act on the seat.
- **Target Zone**: y >= 11.7 m, x in [9.35, 10.65] m.
- **Build Zone**: Any structure (e.g. beams) must be placed within x in [6, 14] m, y in [4, 10] m.
- **Pump Force Limit**: Maximum 42 N horizontal and vertical force per step.

## Task Objective
Design a controller that:
1. Pumps the swing by applying forces.
2. Accounts for wind forces and timing.
3. Energy control to reach the target zone at the apex or through vertical fall.
""",
    "success_criteria": """
## Success Criteria
1. **Target**: Seat reaches the target zone (y >= 11.7 m, x in [9.35, 10.65] m) either (a) at the apex (speed < 1.0 m/s), or (b) via vertical fall into the zone after an apex (|vx| < 1.35 m/s, vy <= 0).

## Design Constraints
- **Mass Budget**: Total structure mass must be less than 100 kg.
- **Build Zone**: Structure must be built within x = [6, 14] m, y = [4, 10] m.
- **Pump Force**: |fx|, |fy| <= 42 N per step.
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['D_04'].values()),
}
