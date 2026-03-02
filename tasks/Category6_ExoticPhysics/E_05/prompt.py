"""
E-05: The Drag Racer task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    APPLY_THRUST,
    GET_BODY_POSITION,
    GET_BODY_VELOCITY,
    GET_STEP_COUNT,
)

TASK_PROMPT = {
    "task_description": """
Design a controller for a drag racer to reach maximum velocity while staying on track in a high-drag environment.

## Task Environment
- **Racer**: A high-speed vehicle subject to exotic drag forces.
- **Track**: A straight course with limited width.
- **Goal**: Reach the finish line at x=50.0m as quickly as possible.

## Task Objective
Design a control loop that:
1. Applies thrust to accelerate the racer toward the finish line.
2. Maintains lateral stability to stay within track bounds.
3. Optimizes acceleration against the environment's drag.
""",
    "success_criteria": """
## Success Criteria
1. **Finish Line**: Racer reaches x >= 50.0m.
2. **Speed**: Minimizes time to completion.
3. **Survival**: Racer stays within lateral track boundaries.

## Design Constraints
- **APIs**: Use only the primitives documented below.
""",
    "primitives_api": API_INTRO
    + GET_BODY_POSITION
    + GET_BODY_VELOCITY
    + GET_STEP_COUNT
    + APPLY_THRUST,
}
