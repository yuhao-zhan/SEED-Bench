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
- **Material**: Small granular particles in a pit.
- **Obstacle**: A central wall at x=0. Use `has_central_wall()` to check environment state.
- **Target Zone**: x > 2.0m.
- **Build Zone**: Base is anchored at x=-2.0m, y=0.5m.

## Task Objective
Design a mechanism that:
1. Scoops up granular material from the pit.
2. Lifts and moves the material over the central wall.
3. Deposits the material into the target zone.
""",
    "success_criteria": """
## Success Criteria
1. **Material Transfer**: Significant amount of granular material moved to the target zone (x > 2.0m).
2. **Integrity**: Mechanism remains intact throughout the operation.

## Design Constraints
- **Mass Budget**: Total structure mass < 300 kg.
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
