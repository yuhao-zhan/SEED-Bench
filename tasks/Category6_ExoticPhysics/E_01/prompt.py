"""
E-01: The Space Bridge task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM,
    ADD_JOINT_RIGID,
    GET_ARENA_BOUNDS,
)

TASK_PROMPT = {
    "task_description": """
Design a bridge in zero-gravity to connect two distant anchor points.

## Task Environment
- **Arena**: A zero-gravity space environment.
- **Anchors**: Two fixed points at x=5.0m and x=25.0m.
- **Goal**: Build a continuous structure between the two anchors.

## Task Objective
Design a bridge that:
1. Spans the entire distance between the anchors.
2. Maintains structural integrity without gravity support.
3. Stays within the arena boundaries.
""",
    "success_criteria": """
## Success Criteria
1. **Connection**: Continuous path of beams and joints exists between anchors.
2. **Integrity**: No joint breaks or detached segments.

## Design Constraints
- **Mass Budget**: Total structure mass < 500 kg.
- **APIs**: Use only the primitives documented below.
""",
    "primitives_api": API_INTRO
    + GET_ARENA_BOUNDS
    + ADD_BEAM
    + ADD_JOINT_RIGID,
}
