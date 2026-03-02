"""
E-03: Slippery World task prompt.
"""
from ...primitives_api import (
    API_INTRO,
    GET_SLED_POSITION,
    GET_SLED_VELOCITY,
    GET_CHECKPOINT_B_REACHED,
    APPLY_THRUST_CRAFT,
)

TASK_PROMPT = {
    "task_description": """
You need to move a sled to a **final target zone** in an environment where friction is nearly zero
(slippery world). Wheels and normal traction do not work; you must use reaction-force propulsion (thrust).

## Task Environment
- **Ground**: Flat surface with very low friction. No grip.
- **Sled**: A rigid body starts near (8, 2) m with very low friction. It cannot get traction by sliding or rolling alone.
- **Final target zone**: A rectangle ahead. The sled center must enter it. Exact bounds in evaluation feedback (target_x_min, target_x_max, target_y_min, target_y_max).
- **Sequence constraint**: The task may require passing through **one or more checkpoints (intermediate zones) in order** before the final target counts. Use get_checkpoint_b_reached() when applicable; feedback reports checkpoint_a_reached, checkpoint_b_reached, checkpoint_reached, and reached_target.
- **Fail condition**: Time runs out without satisfying the success criteria.

## Discoverable phenomena
- **Region-specific effects**: Velocity may drop in some x-ranges (momentum drain); thrust in one direction may produce motion in the opposite direction (reversed thrust); time-varying force may push vertically (crosswind); thrust may be scaled down in some regions; time-varying horizontal force; high speed may be penalized; vertical thrust may be reversed near the final target. Use get_sled_position(), get_sled_velocity(), and feedback to infer.

You may ONLY use the APIs documented below. Do not access internal attributes.
""",
    "success_criteria": """
## Success Criteria
1. **Checkpoints (if required)**: Sled center must have entered each required intermediate zone in order at some time (feedback: checkpoint_a_reached, checkpoint_b_reached, checkpoint_reached).
2. **Final target**: Sled center must enter the final target zone at some time (feedback: reached_target).

## Failure Conditions
- Simulation ends without all required checkpoints being reached in order, or without the final target being reached.
""",
    "primitives_api": API_INTRO
    + """
## Required Code Structure

### 1. build_agent(sandbox)
Return None (sled is pre-built).
### 2. agent_action(sandbox, agent_body, step_count)
Called every step. Read position and velocity; apply thrust. Use get_checkpoint_b_reached() when task requires A then B then final.
"""
    + GET_SLED_POSITION
    + GET_SLED_VELOCITY
    + GET_CHECKPOINT_B_REACHED
    + APPLY_THRUST_CRAFT,
}
