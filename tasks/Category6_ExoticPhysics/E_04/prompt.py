"""
E-04: The Void Bridge task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM,
    ADD_JOINT_RIGID,
    ADD_JOINT_PIVOT,
    GET_BUILD_ZONE,
    GET_GROUND_Y_TOP,
    GET_MIN_BEAMS,
    GET_MIN_JOINTS,
    GET_SPAN_BOUNDS,
    GET_STRUCTURE_MASS,
    GET_STRUCTURE_MASS_LIMIT,
)

TASK_PROMPT = {
    "task_description": """
Design a bridge to span a void in a high-gravity environment.

## Task Environment
- **Void**: A deep gap between two stable surfaces.
- **Gravity**: Significantly higher than standard earth gravity.
- **Goal**: Build a bridge that can support its own weight and any crossing load.

## Task Objective
Design a bridge that:
1. Spans the void while meeting minimum component requirements.
2. Stays within strict total mass limits.
3. Maintains structural integrity under extreme gravity.
""",
    "success_criteria": """
## Success Criteria
1. **Span Completion**: Continuous structure connects both sides of the void.
2. **Structural Stability**: Bridge does not collapse or break joints.
3. **Requirement Adherence**: Meets minimum beam and joint counts within the mass limit.

## Design Constraints
- **Mass Budget**: Total structure mass must be within the limit provided by `get_structure_mass_limit()`.
- **Min Components**: Must use at least the counts provided by `get_min_beams()` and `get_min_joints()`.
- **APIs**: Use only the primitives documented below.
""",
    "primitives_api": API_INTRO
    + GET_GROUND_Y_TOP
    + GET_BUILD_ZONE
    + GET_SPAN_BOUNDS
    + ADD_BEAM
    + ADD_JOINT_RIGID
    + ADD_JOINT_PIVOT
    + GET_STRUCTURE_MASS
    + GET_STRUCTURE_MASS_LIMIT
    + GET_MIN_BEAMS
    + GET_MIN_JOINTS,
}
