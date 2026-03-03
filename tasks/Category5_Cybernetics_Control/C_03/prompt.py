"""
C-03: The Seeker (Very Hard) task Prompt and Primitives definition
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
Design a controller for a seeker craft to achieve multiple heading-aligned rendezvous with a dynamic target.

## Task Environment
- **Seeker**: A craft with a SINGLE thrust vector; thrust is applied only along its current heading. Heading turns at a limited rate toward the commanded direction.
- **Sensing**: `get_target_position()` has variable delay, blind zones, and only updates periodically. You must infer target velocity from position history.
- **Activation Gate**: Rendezvous only counts after the seeker "activates" by staying in the zone x in [13.0, 17.0] m for at least 80 consecutive steps.
- **Moving Corridor**: The seeker must stay within time-varying horizontal bounds. Leaving the corridor fails the run.
- **Wind & Obstacles**: Dynamic wind forces and moving obstacles exist in the corridor.
- **Fuel**: Total thrust impulse is limited; fuel-efficient trajectories are required.

## Task Objective
Design a multi-phase control strategy:
1. **Activation**: Position and hold the seeker in the activation zone until activated.
2. **Slotted Rendezvous**: Achieve two separate rendezvous in narrow time slots (slots are between steps 3720-4780 and 6220-7280).
   - Rendezvous requires: getting close (< 6.0m), matching velocity (rel speed < 1.8 m/s), AND aligning seeker heading with the target's movement direction.
3. **Tracking**: Maintain a close distance to the target after the second rendezvous.
""",
    "success_criteria": """
## Success Criteria
1. **Rendezvous Completion**: Successfully achieve rendezvous in both phase 1 and phase 2 time slots with correct heading alignment.
2. **Tracking**: Maintain distance <= 8.5 m from target after the second rendezvous until the end.
3. **Safety**: No collisions with obstacles; stay within the moving corridor.
4. **Efficiency**: Complete the task within the impulse budget.

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
