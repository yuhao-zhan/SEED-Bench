"""
F-01: The Dam (extreme) task Prompt and Primitives definition
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
Design a free-standing dam to block water particles in an extreme environment.

## Task Environment
- **Water Particles**: 300 particles in a reservoir.
- **Surge Events**: Nine surge waves of increasing intensity will push the water.
- **Debris**: Heavy debris will impact the dam at regular intervals.
- **Build Zone**: Three disjoint narrow vertical strips: x=[12.4, 12.6], [12.9, 13.1], and [13.4, 13.6]. Max height y=7.5m.
- **Constraint**: Mandatory underflow gap; no beams allowed below y=0.5m.
- **Constraint**: ZERO floor anchors; the dam must be free-standing.

## Task Objective
Design a structure that:
1. Blocks water particles such that the leakage rate remains below 0.10%.
2. Maintains structural integrity under surge and debris impact (welds can break).
3. Fits within narrow build strips and respects the underflow requirement.
""",
    "success_criteria": """
## Success Criteria
1. **Leakage Rate**: Total leakage < 0.10%.
2. **Integrity**: Structure does not collapse; all beams must remain connected (no broken joints).

## Design Constraints
- **Mass Budget**: Total structure mass <= 380 kg.
- **Beam Limit**: Maximum 18 beams.
- **Joint Limit**: Maximum 11 beam-to-beam joints.
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
