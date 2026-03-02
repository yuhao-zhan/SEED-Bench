"""
E-04: Variable Mass task prompt.
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM_01_4_EXOTIC,
    ADD_JOINT_GROUND_ANCHOR,
    GET_STRUCTURE_MASS,
    SET_MATERIAL_PROPERTIES_STATICS,
    GET_GROUND_Y_TOP_EXOTIC,
    GET_BUILD_ZONE,
    GET_SPAN_BOUNDS,
    GET_STRUCTURE_MASS_LIMIT,
    GET_MIN_BEAMS,
    GET_MIN_JOINTS,
    BODIES_LIST,
    JOINTS_LIST,
)

TASK_PROMPT = {
    "task_description": """
You need to design a structure in an environment where beam mass varies over time and
the support can experience environmental vibration. Joints can fail if reaction force or
torque is too high; sustained loading may reduce their capacity over time. Your structure
must remain intact for the full evaluation.

## Task Environment
- **Ground**: Support surface at y=0 to y=1 m. Use get_ground_y_top() for anchor placement. The support may be subject to environmental vibration.
- **Mass variation**: Each beam's mass varies over time with multiple frequency components; the exact law is not given — use feedback to infer and adapt.
- **Fail condition**: Structure disintegrates if one or more joints break (reaction force or torque exceeds the joint's current limit). Limits may depend on time and load history.

## Constraints
- **Build zone**: x in [5, 15], y in [1.5, 8]. Use get_build_zone() for exact bounds.
- **Material budget**: Total structure mass ≤ 400 kg. Use get_structure_mass_limit() and get_structure_mass().
- **Minimum complexity**: At least 5 beams and at least 6 joints. Use get_min_beams() and get_min_joints().
- **Span**: Structure must span — at least one beam center x ≤ 6, one ≥ 14. Use get_span_bounds() for (left_x, right_x).
- **At least one pivot**: At least one joint must be type='pivot' (revolute); the rest may be type='rigid'.
- **Anchors**: Use add_joint(body_a, None, anchor_point, ...) to anchor to ground. Use get_ground_y_top() for the y-coordinate of the anchor point on the ground surface.

You may ONLY use the APIs documented below. Do not access internal attributes.
""",
    "success_criteria": """
## Success Criteria
1. **Structure intact**: All joints remain intact; no joint breaks during the run.

## Failure Conditions
- Structure disintegrates: One or more joints break.

## Required Code Structure

### 1. build_agent(sandbox)
Build structure using get_ground_y_top(), get_build_zone(), get_span_bounds(), get_structure_mass_limit(), get_min_beams(), get_min_joints(). Return any beam body.
### 2. agent_action(sandbox, agent_body, step_count)
No per-step action required (purely structural).
""",
    "primitives_api": API_INTRO
    + ADD_BEAM_01_4_EXOTIC
    + ADD_JOINT_GROUND_ANCHOR
    + GET_STRUCTURE_MASS
    + SET_MATERIAL_PROPERTIES_STATICS
    + GET_GROUND_Y_TOP_EXOTIC
    + GET_BUILD_ZONE
    + GET_SPAN_BOUNDS
    + GET_STRUCTURE_MASS_LIMIT
    + GET_MIN_BEAMS
    + GET_MIN_JOINTS
    + BODIES_LIST
    + JOINTS_LIST,
}
