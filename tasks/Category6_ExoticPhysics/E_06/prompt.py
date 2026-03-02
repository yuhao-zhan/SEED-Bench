"""
E-06: The Space Truss task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM,
    ADD_JOINT_RIGID,
    GET_BUILD_ZONE,
    GET_STRUCTURE_MASS,
    GET_STRUCTURE_MASS_LIMIT,
)

TASK_PROMPT = {
    "task_description": """
Design a complex truss structure in zero-gravity to support distributed loads.

## Task Environment
- **Arena**: A zero-gravity space environment.
- **Build Zone**: Defined construction area for the truss.
- **Goal**: Build a truss that remains stable and intact under test loads.

## Task Objective
Design a truss that:
1. Spans the required dimensions within the build zone.
2. Meets specific structural integrity requirements.
3. Stays within strict total mass limits.
""",
    "success_criteria": """
## Success Criteria
1. **Integrity**: Truss remains intact under applied test loads.
2. **Efficiency**: Meets structural requirements within the mass limit provided by `get_structure_mass_limit()`.

## Design Constraints
- **Mass Budget**: Total structure mass must be within the limit provided by `get_structure_mass_limit()`.
- **APIs**: Use only the primitives documented below.
""",
    "primitives_api": API_INTRO
    + GET_BUILD_ZONE
    + ADD_BEAM
    + ADD_JOINT_RIGID
    + GET_STRUCTURE_MASS
    + GET_STRUCTURE_MASS_LIMIT,
}
