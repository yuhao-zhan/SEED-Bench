"""
D-05: The Trebuchet task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM,
    ADD_JOINT_PIVOT,
    ADD_JOINT_RIGID,
    GET_STRUCTURE_MASS,
    SET_MATERIAL_PROPERTIES,
)

TASK_PROMPT = {
    "task_description": """
Design a trebuchet-style launcher to propel a projectile to a target distance.

## Task Environment
- **Ground**: Flat surface at y=1.0m.
- **Build Zone**: x=[0, 10] m, y=[1, 10] m.
- **Target**: Launch the projectile to a distance of at least 25.0m.

## Task Objective
Design a launcher that:
1. Uses a counterweight and a long arm to launch a projectile.
2. Achieves the target launch distance.
3. Maintains structural integrity under dynamic loads.
""",
    "success_criteria": """
## Success Criteria
1. **Distance**: Projectile reaches x >= 25.0m.
2. **Integrity**: Launcher structure remains intact.

## Design Constraints
- **Mass Budget**: Total structure mass < 500 kg.
- **APIs**: Use only the primitives documented below.
""",
    "primitives_api": API_INTRO
    + ADD_BEAM
    + ADD_JOINT_PIVOT
    + ADD_JOINT_RIGID
    + SET_MATERIAL_PROPERTIES
    + GET_STRUCTURE_MASS,
}
