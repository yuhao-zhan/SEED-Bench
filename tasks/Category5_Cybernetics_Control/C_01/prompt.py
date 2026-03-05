"""
C-01: The Cart-Pole Swing-up and Balance task Prompt and Primitives definition
"""

import json
import os

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)


TASK_PROMPT = {
    "task_description": """
Design a controller to swing up a pole from a hanging position and balance it on a moving cart.

## Task Environment
- **Cart**: A body that moves along a horizontal track (center x=10m, safe range ±8.5m).
- **Pole**: Initially hanging downward (angle = 180° or π). **Length**: 2.0m.
- **Oscillation**: The track base oscillates, creating inertial disturbances.
- **Goal**: Swing the pole up to the upright position and keep it balanced (|angle| < 45°) until the end.

## Task Objective
Design a two-phase control strategy:
1. **Swing-up**: Apply horizontal forces to the cart to pump energy into the pole until it reaches the upright region.
2. **Balance**: Once upright, maintain the pole within the balance zone (|angle| < 45°) while staying within track limits.
3. Observe state (angle, velocities) through sensors which may have noise, bias, or delays.
""",
    "success_criteria": """
## Success Criteria
1. **Swing-up & Hold**: Pole reaches the upright region (|angle| <= 45°) and is held there until the end.
2. **Track Limits**: Cart remains within the safe zone (|x - 10| < 8.5m).

## Design Constraints
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': '\n\n'.join(_api_data['C_01'].values()),
}
