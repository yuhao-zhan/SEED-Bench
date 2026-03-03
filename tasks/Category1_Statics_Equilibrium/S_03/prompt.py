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
The structure must extend as far right as possible and support multiple heavy vertical payloads.

## Task Environment
- **Wall**: A vertical static surface at x=0. You may use a maximum of 2 anchor points on this wall. Note that some sections of the wall may be unsuitable for anchoring.
- **Payloads**: Multiple significant weights will be applied to your structure at different times and locations (e.g., at the tip or along the span). Payloads may be attached directly or dropped from above.
- **Obstacles**: The environment may contain static obstructions that you must navigate or build around.
- **Beam Dimensions**: Individual beams have strict limits on width and height to encourage slender cantilever designs.

## Task Objective
Design a robust cantilever structure that can:
1. Extend horizontally from the wall to reach the target distance.
2. Support all applied payloads (stationary or dynamic) without collapsing.
3. Manage internal stresses so that the wall anchors do not exceed their structural strength (overloaded anchors will break).
4. **Stiffness**: Maintain vertical stability under load. If the structure sags beyond the allowed threshold, the task fails.

## Instructions
1. **Analyze Environment**: Observe feedback to identify obstacle locations and forbidden anchor zones.
2. **Triangulate**: Use efficient truss geometry to minimize torque at the wall anchors.
3. **Reinforce**: Ensure the structure is stiff enough to catch falling payloads if necessary.
""",
    
    'success_criteria': """
## Success Criteria
1. **Reach**: Structure reaches the required horizontal distance.
2. **Load Bearing**: Successfully supports all payloads for the duration of the test.
3. **Anchor Integrity**: All wall anchors remain intact (no breakage due to excessive torque).
4. **Stability**: The structure does not sag below the failure limit.

## Design Constraints
- **Anchor Limit**: Maximum 2 anchor points on the wall.
- **Strength Limits**: Wall joints have finite capacity; excessive torque will cause them to snap.
- **Geometry**: The structure must reach the target and provide suitable nodes for payload attachment.
- **APIs**: Use only the primitives documented below.
""",
    
    'primitives_api': API_INTRO + ADD_BEAM + ADD_JOINT_RIGID + GET_STRUCTURE_MASS + GET_STRUCTURE_REACH + ACCESS_TERRAIN_BODIES,
}
