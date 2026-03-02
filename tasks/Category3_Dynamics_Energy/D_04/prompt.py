"""
D-04: The Swing task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    APPLY_FORCE_TO_SEAT,
    APPLY_IMPULSE_TO_SEAT,
    GET_SIM_TIME,
    GET_SWING_SEAT,
    GET_WIND_FORCE_AT_TIME,
)

TASK_PROMPT = {
    "task_description": """
Design a control strategy to pump a swing seat to reach a target zone.

## Task Environment
- **Swing Seat**: A heavy body attached to a fixed pivot at (10, 10) m.
- **Wind**: Time-varying wind forces act on the seat.
- **Target Zone**: y >= 11.7 m, x in [9.35, 10.65] m.
- **Pump Force Limit**: Maximum 42 N horizontal force per step.

## Task Objective
Design a controller that:
1. Pumps the swing by applying horizontal forces.
2. Accounts for wind forces and timing.
3. Energy control to reach the target zone at the apex or through vertical fall.
""",
    "success_criteria": """
## Success Criteria
1. **Target**: Seat reaches the target zone (y >= 11.7m, x around 10.0m) at the apex (speed < 1.0 m/s) or via vertical fall.

## Design Constraints
- **Pump Force**: |fx| <= 42 N per step.
- **APIs**: Use only the primitives documented below.
""",
    "primitives_api": API_INTRO
    + GET_SWING_SEAT
    + APPLY_FORCE_TO_SEAT
    + APPLY_IMPULSE_TO_SEAT
    + GET_WIND_FORCE_AT_TIME
    + GET_SIM_TIME,
}
