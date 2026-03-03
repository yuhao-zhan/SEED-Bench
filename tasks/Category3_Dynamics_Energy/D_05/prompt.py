"""
D-05: The Hammer task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM,
    ADD_JOINT_PIVOT,
    ADD_JOINT_RIGID,
    GET_STRUCTURE_MASS,
    SET_MATERIAL_PROPERTIES,
    JOINTS_LIST,
)

TASK_PROMPT = {
    "task_description": """
Design a hammer mechanism to break a hard shell located behind a protective barrier.

## Task Environment
- **The Shell**: A breakable target at x=16.0m, y=2.6m. It requires a large instantaneous force to break.
- **The Slot Barrier**: A wall at x=15.0m with a narrow vertical gap. Your hammer head must pass through this gap.
- **The Oscillating Bar**: A horizontal bar inside the slot gap that moves up and down. You must time your swing to pass when the bar is away.
- **Obstacles**: A swinging pendulum at x=7.0m may block your swing.
- **Build Zone**: x=[2.0, 12.0] m, y=[2.0, 8.0] m. You must anchor your mechanism to the ground.

## Task Objective
Design a hammer that:
1. Is anchored to the ground and consists of a handle and a heavy head.
2. Achieves a trajectory that passes through the narrow slot gap without hitting the walls or the oscillating bar.
3. Delivers a strike with enough kinetic energy and force (> 5000 N) to break the shell.
""",
    "success_criteria": """
## Success Criteria
1. **Breakage**: The shell at x=16.0m must be broken by the impact.
2. **Precision**: The hammer must not collide with the slot walls, the oscillating bar, or the pendulum.

## Design Constraints
- **Mass Budget**: Total structure mass < 70.0 kg.
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': API_INTRO + ADD_BEAM + ADD_JOINT_RIGID + ADD_JOINT_PIVOT + SET_MATERIAL_PROPERTIES + GET_STRUCTURE_MASS + JOINTS_LIST,
}
