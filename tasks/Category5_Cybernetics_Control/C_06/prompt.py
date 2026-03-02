"""
C-06: The Wheel Control task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    APPLY_MOTOR_TORQUE,
    GET_TARGET_SPEED,
    GET_WHEEL_ANGULAR_VELOCITY,
    GET_WHEEL_BODY,
)

TASK_PROMPT = {
    "task_description": """
Design a controller to maintain a wheel at a target angular velocity.

## Task Environment
- **Wheel**: A circular body that can rotate.
- **Motor**: Provides torque to the wheel.
- **Goal**: Match and maintain the target angular velocity.

## Task Objective
Design a control loop that:
1. Observes the current angular velocity of the wheel.
2. Identifies the current target speed (which may change).
3. Applies motor torque to minimize the error between current and target speeds.
""",
    "success_criteria": """
## Success Criteria
1. **Speed Matching**: Wheel angular velocity stays close to target speed for a sustained duration.

## Design Constraints
- **APIs**: Use only the primitives documented below.
""",
    "primitives_api": API_INTRO
    + GET_WHEEL_BODY
    + GET_WHEEL_ANGULAR_VELOCITY
    + GET_TARGET_SPEED
    + APPLY_MOTOR_TORQUE,
}
