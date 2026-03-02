"""
C-01: The Cart-Pole task Prompt and Primitives definition
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
Design a controller to balance a pole on a cart by applying horizontal forces.

## Task Environment
- **Cart**: A body that moves along a horizontal track.
- **Pole**: A body attached to the cart via a pivot joint.
- **Goal**: Keep the pole upright (near angle=0) for at least 15.0 seconds.

## Task Objective
Design a control loop that:
1. Observes the pole angle and angular velocity.
2. Observes the cart position and velocity.
3. Applies a horizontal force to the cart to maintain balance and stay near the center of the track.
""",
    "success_criteria": """
## Success Criteria
1. **Balance**: Pole remains upright (|angle| < 15 degrees) for >= 15.0 seconds.
2. **Track Limits**: Cart remains within track bounds (|x| < 4.0m).

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
