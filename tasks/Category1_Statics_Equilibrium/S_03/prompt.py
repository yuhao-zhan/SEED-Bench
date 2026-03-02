"""
S-03: The Cantilever task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM,
    ADD_JOINT_RIGID,
    GET_STRUCTURE_MASS,
    GET_STRUCTURE_REACH,
    ACCESS_TERRAIN_BODIES,
)

TASK_PROMPT = {
    'task_description': """
Construct a horizontal cantilever structure anchored ONLY to the left wall.
The structure must extend as far right as possible and support two significant vertical loads applied at different times.

## Task Environment
- **Wall**: A vertical static wall at x=0. You may use a maximum of 2 anchor points on this wall.
- **Load 1 (Tip)**: A heavy weight will attach to your right-most structural node after an initial period.
- **Load 2 (Mid-span)**: A second heavy weight will attach later to a node within the x=[5, 10] range. You must ensure your design includes a node in this range (the node closest to x=7.5m will be selected).
- **Beam Dimensions**: 0.1 <= width <= 10.0 m, 0.1 <= height <= 2.0 m. Beams are restricted in height to encourage slender cantilever designs.

## Task Objective
Design a robust cantilever structure that can:
1. Extend horizontally from the wall to reach at least x=14m.
2. Support both the tip load and the mid-span load simultaneously without collapsing.
3. Use no more than 2 wall anchors. Distribute the internal stresses so that the anchors do not exceed their structural strength (overloaded anchors will break).
4. **Stiffness**: Maintain vertical position under load. If the tip sags significantly (below y=-2.5m), the task fails.
""",
    
    'success_criteria': """
## Success Criteria
1. **Reach**: Structure reaches x >= 14m.
2. **Load Bearing**: Successfully holds both loads for the duration of the test.
3. **Anchor Integrity**: All wall anchors remain intact (no breakage due to excessive torque).
4. **Stiffness**: The structure does not sag below the limit (y > -2.5m).

## Design Constraints
- **Anchor Limit**: Maximum 2 anchor points on the wall.
- **Anchor Strength**: Wall joints will break if subjected to excessive torque.
- **Node Requirement**: Must provide at least one node in x=[5, 10] for the second load.
- **APIs**: Use only the primitives documented below.
""",
    
    'primitives_api': API_INTRO + ADD_BEAM + ADD_JOINT_RIGID + GET_STRUCTURE_MASS + GET_STRUCTURE_REACH + ACCESS_TERRAIN_BODIES,
}
