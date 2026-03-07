"""
C-01: The Cart-Pole Swing-up and Balance task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'C_01' in _api_data and 'API_INTRO' in _api_data['C_01']:
    del _api_data['C_01']['API_INTRO']


TASK_PROMPT = {
    "task_description": """
Design a controller to maintain a pole balanced on a moving cart.

## Task Environment
- **Cart**: A body that moves along a horizontal track (center x=10m, safe range ±8.5m).
- **Pole**: Initially upright (angle = 0° or 0rad). **Length**: 2.0m.
- **Goal**: Maintain the pole in the upright position (|angle| <= 45°) until the end.

## Task Objective
Design a control strategy:
1. **Balance**: Maintain the pole within the balance zone (|angle| <= 45°) while staying within track limits.
2. Observe state (angle, velocities) through sensors which may have noise, bias, or delays.
""",
    "success_criteria": """
## Success Criteria
1. **Stability**: Pole is held within the upright region (|angle| <= 45°) until the end.
2. **Track Limits**: Cart remains within the safe zone (|x - 10| < 8.5m).

## Design Constraints
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['C_01'].values()),
}
