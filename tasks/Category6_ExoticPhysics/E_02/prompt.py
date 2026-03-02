"""
E-02: The Thick Air task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    APPLY_THRUST,
    GET_CRAFT_POSITION,
    GET_HEAT,
    GET_OVERHEAT_LIMIT,
    GET_STEP_COUNT,
    IS_OVERHEATED,
)

TASK_PROMPT = {
    "task_description": """
Design a controller for a craft navigating through a high-friction, "thick air" environment.

## Task Environment
- **Craft**: A vehicle subject to intense drag and heating.
- **Goal**: Reach a target coordinate while managing internal heat levels.
- **Heat**: Applying thrust increases craft heat. Overheating causes mission failure.

## Task Objective
Design a control loop that:
1. Navigates the craft toward the target position.
2. Monitors heat levels and manages thrust to avoid overheating.
3. Successfully reaches the target within simulation time limits.
""",
    "success_criteria": """
## Success Criteria
1. **Target Reach**: Craft reaches the target position.
2. **Thermal Safety**: Craft does not overheat during the mission.

## Design Constraints
- **APIs**: Use only the primitives documented below.
""",
    "primitives_api": API_INTRO
    + GET_CRAFT_POSITION
    + IS_OVERHEATED
    + GET_HEAT
    + GET_OVERHEAT_LIMIT
    + GET_STEP_COUNT
    + APPLY_THRUST,
}
