"""
C-02: The Lunar Lander task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    APPLY_THRUST,
    GET_GROUND_Y_TOP,
    GET_LANDER_ANGLE,
    GET_LANDER_ANGULAR_VELOCITY,
    GET_LANDER_BODY,
    GET_LANDER_POSITION,
    GET_LANDER_SIZE,
)

TASK_PROMPT = {
    "task_description": """
Design a controller to safely land a craft on a landing pad by controlling thrust and steering.

## Task Environment
- **Lander**: A craft that spawns at a high altitude.
- **Goal**: Reach the landing pad (near x=0, ground level) with low velocity and upright orientation.
- **Thrust**: Main engine provides upward thrust; steering thrusters provide torque.

## Task Objective
Design a control loop that:
1. Observes the lander's position, velocity, and orientation.
2. Applies thrust and steering torque to control descent.
3. Successfully lands on the pad within specified safety limits.
""",
    "success_criteria": """
## Success Criteria
1. **Soft Landing**: Land on the pad with low downward velocity (|vy| < 2.0 m/s).
2. **Upright Orientation**: Land with the lander nearly upright (|angle| < 10 degrees).
3. **Accuracy**: Land within the landing pad's horizontal bounds.

## Design Constraints
- **APIs**: Use only the primitives documented below.
""",
    "primitives_api": API_INTRO
    + GET_LANDER_BODY
    + GET_LANDER_POSITION
    + GET_LANDER_ANGLE
    + GET_LANDER_ANGULAR_VELOCITY
    + GET_GROUND_Y_TOP
    + GET_LANDER_SIZE
    + APPLY_THRUST,
}
