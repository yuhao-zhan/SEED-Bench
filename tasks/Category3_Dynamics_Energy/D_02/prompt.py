"""
D-02: The Jumper task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    SET_VELOCITY,
    GET_BODY_POSITION,
)

TASK_PROMPT = {
    "task_description": """
Design a jumping mechanism to clear a pit and land on a distant platform by passing through multiple narrow slots.

## Task Environment
- **Platforms**: A left platform (start) and a right platform (target) separated by a wide pit.
- **Barriers**: Multiple vertical barriers with narrow horizontal slots (gaps) are positioned between the platforms.
- **Build Zone**: x in [5.0, 15.0] m, y in [1.5, 8.0] m.
- **Goal**: Reach the right platform (x >= 26.0m) by jumping from the left platform.

## Task Objective
Design a controller that:
1. Determines the optimal launch velocity (magnitude and direction) to jump over the pit.
2. Ensures the trajectory passes through the narrow gaps in all intermediate barriers.
3. Successfully lands on the right platform without falling into the pit or hitting the red sections of the barriers.
""",
    "success_criteria": """
## Success Criteria
1. **Target Reach**: Body reaches the right platform (x >= 26.0m, y >= 1.0m).
2. **Gap Clearance**: Trajectory successfully passes through all barrier slots without collision.

## Design Constraints
- **APIs**: Use only the primitives documented below.
""",
    "primitives_api": API_INTRO
    + GET_BODY_POSITION
    + SET_VELOCITY,
}
