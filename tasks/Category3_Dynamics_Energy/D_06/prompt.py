"""
D-06: The Demolition task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM,
    ADD_JOINT_RIGID,
    GET_STRUCTURE_MASS,
    SET_MATERIAL_PROPERTIES,
)

TASK_PROMPT = {
    "task_description": """
Design a structure to withstand or absorb energy from falling demolition blocks.

## Task Environment
- **Ground**: Flat surface at y=1.0m.
- **Demolition Blocks**: Heavy blocks fall from y=10.0m.
- **Build Zone**: x=[5, 15] m, y=[1, 5] m.
- **Target**: Protect a designated area or object below the falling path.

## Task Objective
Design a structure that:
1. Absorbs the kinetic energy of falling blocks.
2. Maintains its integrity and protects the target zone.
3. Stays within mass and beam count limits.
""",
    "success_criteria": """
## Success Criteria
1. **Protection**: Target zone remains protected from falling block impacts.
2. **Integrity**: Structure does not collapse under impact.

## Design Constraints
- **Mass Budget**: Total structure mass < 300 kg.
- **Beam Limit**: Maximum 25 beams.
- **APIs**: Use only the primitives documented below.
""",
    "primitives_api": API_INTRO
    + ADD_BEAM
    + ADD_JOINT_RIGID
    + SET_MATERIAL_PROPERTIES
    + GET_STRUCTURE_MASS,
}
