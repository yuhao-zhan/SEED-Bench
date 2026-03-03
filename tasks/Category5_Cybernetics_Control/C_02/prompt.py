"""
C-02: The Lander (obstacle + moving platform) task Prompt and Primitives definition
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
Design a controller to safely land a craft on a moving platform while navigating around a no-fly zone.

## Task Environment
- **Lander**: A craft starting at a high altitude.
- **No-Fly Zone**: A horizontal obstacle located at x in [12.0, 18.0] m, y in [10.0, 11.0] m. Collisions with this zone must be avoided.
- **Landing Zone**: A moving platform on the ground. Its center oscillates around x=15.0m with an amplitude of 2.5m. The valid landing area is 4.0m wide (center ± 2.0m) and its position depends on the time of landing.
- **Thrust**: Main engine provides upward thrust; steering thrusters provide torque.
- **Impulse Budget**: You have a limited fuel supply. You must land with a significant portion of your impulse budget remaining.

## Task Objective
Design a control loop that:
1. Navigates the lander around the no-fly zone (e.g., by going above or around it).
2. Tracks the moving landing zone and times the descent accordingly.
3. Successfully soft-lands on the platform within specified safety and fuel-efficiency limits.
""",
    "success_criteria": """
## Success Criteria
1. **Soft Landing**: Land on the platform with low downward velocity (|vy| < 2.0 m/s).
2. **Upright Orientation**: Land with the craft nearly upright (|angle| < 10 degrees).
3. **Accuracy**: Land within the platform's horizontal bounds at the moment of contact.
4. **Efficiency**: Land with at least 450 N·s of impulse budget remaining.

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
