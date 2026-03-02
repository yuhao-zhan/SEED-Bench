"""
F-01: The Filtration task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM,
    ADD_JOINT_RIGID,
    GET_STRUCTURE_MASS,
    SET_MATERIAL_PROPERTIES,
    GET_TERRAIN_JOINT_COUNT,
    BODIES_LIST,
    JOINTS_LIST,
)

TASK_PROMPT = {
    "task_description": """
Design a filtration structure to separate larger granular particles from smaller ones.

## Task Environment
- **Particles**: A mix of small and large particles will flow through the structure.
- **Build Zone**: x=[10, 20] m, y=[2, 8] m.
- **Target**: Retain large particles while allowing small ones to pass through.

## Task Objective
Design a filter that:
1. Effectively blocks large particles.
2. Minimizes the blockage of small particles.
3. Maintains structural stability under the weight of the particles.
""",
    "success_criteria": """
## Success Criteria
1. **Filtration**: High ratio of large particles retained vs small particles passed.
2. **Integrity**: Structure does not collapse or break joints.

## Design Constraints
- **Mass Budget**: Total structure mass < 150 kg.
- **Beam Limit**: Maximum 30 beams.
- **Joint Limit**: Maximum 40 joints.
- **APIs**: Use only the primitives documented below.
""",
    "primitives_api": API_INTRO
    + ADD_BEAM
    + ADD_JOINT_RIGID
    + SET_MATERIAL_PROPERTIES
    + GET_STRUCTURE_MASS
    + GET_TERRAIN_JOINT_COUNT
    + BODIES_LIST
    + JOINTS_LIST,
}
