"""
F-03: The Excavator task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_ANCHORED_BASE,
    ADD_BEAM,
    ADD_JOINT_RIGID,
    ADD_REVOLUTE_JOINT,
    ADD_SCOOP,
    HAS_CENTRAL_WALL,
    SET_MOTOR,
    SET_MATERIAL_PROPERTIES,
)

TASK_PROMPT = {
    "task_description": """
Design an excavator arm and scoop to move granular material over an obstacle.

## Task Environment
## Task Environment
- **Material**: 200 high-friction sand particles in a pit located between x=0.0m and x=5.0m.
- **Obstacle**: A central wall at x=-1.0m. Use `has_central_wall()` to check environment state.
- **Target Hopper**: Located at x=-5.0m, y=3.0m.
- **Build Zone**: Mechanism must be built in x=[-4.0, 2.0], y=[0.0, 5.0]. Base is anchored at x=-2.0m, y=0.0m.
- **Time Limit**: Complete the task within 40 seconds.

## Task Objective
Design a mechanism that:
1. Scoops up granular material from the pit (x > 0).
2. Lifts and moves the material over the central wall (x = -1.0).
3. Deposits the material into the target hopper at x=-5.0.
...
## Success Criteria
1. **Material Transfer**: At least 50 sand particles are deposited in the hopper (x=-5.0, y=3.0).

2. **Integrity**: Mechanism remains intact throughout the operation.

## Design Constraints
- **Mass Budget**: Total structure mass <= 800 kg.
- **APIs**: Use only the primitives documented below.
""",
    "primitives_api": API_INTRO
    + ADD_ANCHORED_BASE
    + ADD_BEAM
    + ADD_JOINT_RIGID
    + ADD_REVOLUTE_JOINT
    + ADD_SCOOP
    + SET_MOTOR
    + SET_MATERIAL_PROPERTIES
    + HAS_CENTRAL_WALL,
}
