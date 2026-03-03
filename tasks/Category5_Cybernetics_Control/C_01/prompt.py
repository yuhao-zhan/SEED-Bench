"""
C-01: The Cart-Pole Swing-up and Balance task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    APPLY_CART_FORCE,
    GET_CART_BODY,
    GET_CART_POSITION,
    GET_CART_VELOCITY,
    GET_POLE_ANGLE,
    GET_POLE_ANGULAR_VELOCITY,
)

TASK_PROMPT = {
    "task_description": """
Design a controller to swing up a pole from a hanging position and balance it on a moving cart.

## Task Environment
- **Cart**: A body that moves along a horizontal track (center x=10m, safe range ±8.5m).
- **Pole**: Initially hanging downward (angle = 180° or π).
- **Oscillation**: The track base oscillates, creating inertial disturbances.
- **Goal**: Swing the pole up to the upright position and keep it balanced (|angle| < 110°) until the end.

## Task Objective
Design a two-phase control strategy:
1. **Swing-up**: Apply horizontal forces to the cart to pump energy into the pole until it reaches the upright region.
2. **Balance**: Once upright, maintain the pole within the balance zone while staying within track limits.
3. Observe state (angle, velocities) through sensors which may have noise, bias, or delays.
""",
    "success_criteria": """
## Success Criteria
1. **Swing-up & Hold**: Pole reaches the upright region (|angle| <= 110°) and is held there until the end.
2. **Track Limits**: Cart remains within the safe zone (|x - 10| < 8.5m).

## Design Constraints
- **APIs**: Use only the primitives documented below.
""",
    "primitives_api": API_INTRO
    + GET_CART_BODY
    + GET_POLE_ANGLE
    + GET_POLE_ANGULAR_VELOCITY
    + GET_CART_POSITION
    + GET_CART_VELOCITY
    + APPLY_CART_FORCE,
}
