"""
E-03: The Sled task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    APPLY_THRUST,
    GET_CHECKPOINT_B_REACHED,
    GET_SLED_POSITION,
    GET_SLED_VELOCITY,
)

TASK_PROMPT = {
    "task_description": """
Design a controller for a sled to navigate through a low-friction environment and pass through checkpoints.

## Task Environment
- **Sled**: A sliding body subject to thrust and minimal friction.
- **Checkpoints**: Target locations that must be reached in order.
- **Goal**: Pass through all checkpoints within the time limit.

## Task Objective
Design a control loop that:
1. Directs the sled toward the next checkpoint.
2. Manages speed and orientation to successfully pass through checkpoints.
3. Adapts to the low-friction dynamics of the environment.
""",
    "success_criteria": """
## Success Criteria
1. **Checkpoint Completion**: Sled passes through all required checkpoints.
2. **Target Reach**: Sled center enters the final target zone (x in [28, 32], y in [2.2, 2.8]).
3. **Efficiency**: Reaches the final target within the time limit.

## Design Constraints
- **APIs**: Use only the primitives documented below.
""",
    "primitives_api": API_INTRO
    + GET_SLED_POSITION
    + GET_SLED_VELOCITY
    + GET_CHECKPOINT_B_REACHED
    + APPLY_THRUST,
}
