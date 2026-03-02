"""
D-02: The Jumper task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM,
    ADD_JOINT_RIGID,
    GET_JUMPER,
    GET_STRUCTURE_MASS,
    SET_JUMPER_VELOCITY,
    SET_MATERIAL_PROPERTIES,
)

TASK_PROMPT = {
    "task_description": """
Design a jumping mechanism that allows a jumper body to reach a target platform.

## Task Environment
- **Starting Position**: The jumper starts on the ground at x=5.0m, y=1.5m.
- **Target Platform**: Located at x=15.0m, y=6.0m.
- **Build Zone**: x=[0, 10] m, y=[1, 5] m. All structural components must be placed within this zone.
- **Success Criteria**: The jumper body must land and stay on the target platform for at least 2.0 seconds.

## Task Objective
Design a mechanism that:
1. Provides the necessary initial velocity to the jumper.
2. Uses structural components to support or guide the jump.
3. Ensures the jumper reaches and stabilizes on the target platform.
""",
    "success_criteria": """
## Success Criteria
1. **Reach**: Jumper reaches the target platform (y >= 6.0m, x around 15.0m).
2. **Stability**: Jumper stays on the platform for >= 2.0 seconds.

## Design Constraints
- **Mass Budget**: Total structure mass < 200 kg.
- **APIs**: Use only the primitives documented below.
""",
    "primitives_api": API_INTRO
    + GET_JUMPER
    + ADD_BEAM
    + ADD_JOINT_RIGID
    + SET_MATERIAL_PROPERTIES
    + SET_JUMPER_VELOCITY
    + GET_STRUCTURE_MASS,
}
