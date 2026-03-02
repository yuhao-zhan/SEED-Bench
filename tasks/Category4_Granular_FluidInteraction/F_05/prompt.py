"""
F-05: The Cargo Boat task Prompt and Primitives definition
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
Design a cargo containment structure for a boat to transport granular material across a fluid environment.

## Task Environment
- **Boat**: A static or motorized boat body.
- **Cargo**: Granular particles loaded onto the boat.
- **Build Zone**: Structure must be attached to the boat body.
- **Target**: Transport cargo to x=30.0m without losing a significant portion.

## Task Objective
Design containment that:
1. Prevents cargo from falling overboard.
2. Maintains the boat's stability and buoyancy.
3. Withstands the dynamic forces of fluid and motion.
""",
    "success_criteria": """
## Success Criteria
1. **Cargo Retention**: Significant percentage of initial cargo reaches the target.
2. **Stability**: Boat does not capsize or sink.

## Design Constraints
- **Mass Budget**: Total containment mass < 150 kg.
- **APIs**: Use only the primitives documented below.
""",
    "primitives_api": API_INTRO
    + ADD_BEAM
    + ADD_JOINT_RIGID
    + SET_MATERIAL_PROPERTIES
    + GET_STRUCTURE_MASS,
}
