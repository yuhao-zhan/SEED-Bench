"""
C-02: The Lander (obstacle + moving platform) task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'C_02' in _api_data and 'API_INTRO' in _api_data['C_02']:
    del _api_data['C_02']['API_INTRO']


TASK_PROMPT = {
    "task_description": """
Design a controller to safely land a craft on a moving platform while navigating around a no-fly zone.

## Task Environment
- **Lander**: A craft starting at a high altitude (spawn x=6.0m, y=12.0m).
- **No-Fly Zone**: A vertical barrier located at x in [10.5, 13.5] m, extending from the ground up to y=6.0m. Collisions with this zone must be avoided.
- **Landing Zone**: A moving platform on the ground. Its center oscillates around x=17.0m with an amplitude of 1.8m. The valid landing area is 4.0m wide (center ± 2.0m) and its position depends on the time of landing.
- **Thrust**: Main engine provides upward thrust; steering thrusters provide torque.
- **Impulse Budget**: You have a limited fuel supply. You must land with a significant portion of your impulse budget remaining.

## Task Objective
Design a control loop that:
1. Navigates the lander around the no-fly zone (e.g., by climbing above or flying around the barrier).
2. Tracks the moving landing zone and times the descent accordingly.
3. Successfully soft-lands on the platform within specified safety and fuel-efficiency limits.
""",
    "success_criteria": """
## Success Criteria
1. **Soft Landing**: Land on the platform with low downward velocity (|vy| <= 2.0 m/s).
2. **Upright Orientation**: Land with the craft nearly upright (|angle| <= 10 degrees).
3. **Accuracy**: Land within the platform's horizontal bounds at the moment of contact.
4. **Efficiency**: Land with at least 450 N·s of impulse budget remaining.

## Design Constraints
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['C_02'].values()),
}
