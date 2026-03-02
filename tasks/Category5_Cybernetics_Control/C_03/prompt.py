"""
C-03: The Seeker task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    APPLY_SEEKER_FORCE,
    GET_CORRIDOR_BOUNDS,
    GET_LOCAL_WIND,
    GET_REMAINING_IMPULSE_BUDGET,
    GET_SEEKER_BODY,
    GET_SEEKER_HEADING,
    GET_SEEKER_POSITION,
    GET_SEEKER_VELOCITY,
    GET_TARGET_POSITION,
    GET_TERRAIN_OBSTACLES,
)

TASK_PROMPT = {
    "task_description": """
Design a controller for a seeker craft to navigate a corridor, avoid obstacles, and reach a moving target.

## Task Environment
- **Seeker**: A small craft with a limited impulse budget.
- **Corridor**: Horizontal bounds that the seeker must stay within.
- **Obstacles**: Static or dynamic obstacles that must be avoided.
- **Target**: A moving destination point.
- **Wind**: Local wind forces act on the seeker.

## Task Objective
Design a control loop that:
1. Navigates the corridor while avoiding collisions.
2. Manages the limited impulse budget effectively.
3. Successfully reaches the target position.
""",
    "success_criteria": """
## Success Criteria
1. **Target Reach**: Seeker reaches the target position.
2. **Survival**: No collisions with obstacles or corridor walls.
3. **Efficiency**: Reaches target within the impulse budget.

## Design Constraints
- **APIs**: Use only the primitives documented below.
""",
    "primitives_api": API_INTRO
    + GET_SEEKER_BODY
    + GET_SEEKER_POSITION
    + GET_SEEKER_VELOCITY
    + GET_SEEKER_HEADING
    + GET_TARGET_POSITION
    + GET_TERRAIN_OBSTACLES
    + GET_LOCAL_WIND
    + GET_REMAINING_IMPULSE_BUDGET
    + GET_CORRIDOR_BOUNDS
    + APPLY_SEEKER_FORCE,
}
