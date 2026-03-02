"""
E-05: The Magnet task prompt.
"""
from ...primitives_api import (
    API_INTRO,
    GET_BODY_POSITION,
    GET_BODY_VELOCITY,
    GET_STEP_COUNT,
    APPLY_THRUST_CRAFT,
)

TASK_PROMPT = {
    "task_description": """
You need to move a body to a target zone in an environment with invisible force fields.
You control the body via thrust only. The fields can create local minima and block direct paths.

## Task Environment
- **Ground**: Flat surface. Body rests on it when low enough.
- **Body**: A rigid body starts at (8, 5) m. It experiences gravity.
- **Invisible force fields**: Repulsive and attractive fields exist. Their layout, number, and behavior are unknown — infer from motion, position, and velocity feedback.
- **Target zone**: Body center must enter x in [28, 32] m, y in [8.2, 9.5] m. The target is elevated.
- **Fail condition**: Stuck — the body never reaches the target zone before time runs out.

## Constraints
- **Thrust**: Magnitude may be limited by the environment. Use get_step_count() for timing (e.g. fields may oscillate).

You may ONLY use the APIs documented below. Do not access internal attributes.
""",
    "success_criteria": """
## Success Criteria
- **Reach target**: Body center enters the zone (x in [28, 32], y in [8.2, 9.5]) at some time.

## Failure Conditions
- **Stuck**: Simulation ends without ever entering the target zone.
""",
    "primitives_api": API_INTRO
    + """
## Required Code Structure

### 1. build_agent(sandbox)
Return None (body is pre-built).
### 2. agent_action(sandbox, agent_body, step_count)
Called every step. Read position and velocity; apply thrust. Use get_step_count() for timing.
"""
    + GET_BODY_POSITION
    + GET_BODY_VELOCITY
    + GET_STEP_COUNT
    + APPLY_THRUST_CRAFT,
}
