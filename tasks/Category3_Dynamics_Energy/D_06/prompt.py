"""
D-06: The Catch task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM,
    ADD_JOINT_RIGID,
    ADD_JOINT_PIVOT,
    GET_STRUCTURE_MASS,
    SET_MATERIAL_PROPERTIES,
    JOINTS_LIST,
)

TASK_PROMPT = {
    "task_description": """
Design a structure to catch and stabilize seven heavy balls launched sequentially toward a target zone.

## Task Environment
- **The Projectiles**: Seven balls are launched from the right (x=22.0m) toward the left. They arrive at different times and heights.
- **The Deflector**: A moving bar at x=8.36m will deflect the balls. You should use it to your advantage.
- **Forbidden Zones**: Beam centers must not be placed in five specific vertical zones (e.g., x=[8.5, 9.5], x=[7.35, 7.75]).
- **Sweeper Bands**: Two horizontal bands (y=[2.95, 3.55] and y=[4.15, 4.75]) are forbidden for any beam centers.
- **Build Zone**: x=[7.0, 11.0] m, y=[0.5, 5.5] m. The structure must be anchored to the ground.

## Task Objective
Design a catching structure that:
1. Absorbs the kinetic energy of all seven balls.
2. Keeps all balls within the target zone (x=[7, 11], y=[0.5, 5.5]) with a final speed < 0.35 m/s.
3. Handles sequential arrivals: each ball must be caught before the next one arrives to avoid ball-ball collisions.
""",
    "success_criteria": """
## Success Criteria
1. **Catch All**: All seven balls must be caught and stabilized within the target area.
2. **Order**: Balls must be processed sequentially without pile-ups.
3. **Integrity**: The structure must not break under the impact forces (max joint force < 880 N).

## Design Constraints
- **Beam Limit**: Maximum 9 beams.
- **Mass Budget**: Total structure mass < 10.0 kg.
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': API_INTRO + ADD_BEAM + ADD_JOINT_RIGID + ADD_JOINT_PIVOT + SET_MATERIAL_PROPERTIES + GET_STRUCTURE_MASS + JOINTS_LIST,
}
