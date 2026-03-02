"""
E-06: Cantilever Endurance task prompt.
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM_01_4_EXOTIC,
    ADD_JOINT_GROUND_ANCHOR,
    GET_STRUCTURE_MASS,
    SET_MATERIAL_PROPERTIES_STATICS,
    GET_BUILD_ZONE,
    GET_STRUCTURE_MASS_LIMIT,
)

TASK_PROMPT = {
    "task_description": """
You need to design a **cantilever structure** that **survives** hostile excitation
(no joint or beam failure). The environment is fundamentally hard: very limited anchoring,
tight mass budget, geometry restrictions, and spatial variation in load and damage.

## Task Environment
- **Ground**: Flat surface at y=0 to y=1 m.
- **Support**: Very limited ground anchors; invalid placement is rejected. Use feedback to infer allowed count and positions. Structure must cantilever from this support (no support under the span).
- **Build geometry**: Beam placement may be rejected in certain regions (e.g. forbidden zone). Use build errors to infer restricted zones and route around them.
- **Excitation**: Random impulses and coherent pulses; spatial/temporal pattern not specified — infer from failure and stress feedback.
- **Damage**: Joints fail under stress; damage may accumulate faster in some regions. Beams that spin excessively can be destroyed.
- **Tip stability**: Feedback reports how often the rightmost tip stays in a vertical band; use it to tune stiffness and bracing.

## Constraints
- **Build zone**: x in [5, 15], y in [1.5, 8]. Use get_build_zone() for exact bounds.
- **Material budget**: Total structure mass ≤ 120 kg. Use get_structure_mass_limit() and get_structure_mass().
- **Anchors**: Very limited (e.g. only one ground anchor allowed in support zone x in [5, 6.5]); use feedback to find valid count and positions.
- **Beam limits**: 0.1 ≤ width, height ≤ 4.0 m.
- **Span**: Structure must span and reach required height; feedback indicates failures.

You may ONLY use the APIs documented below. Do not access internal attributes.
""",
    "success_criteria": """
## Success Criteria
1. **Structure intact**: All joints and beams remain; no disintegration (primary).

## Failure Conditions
- **Fatigue**: Joint(s) break or beam(s) destroyed.
- **Design constraint**: Build zone, mass, span, geometry, or topology violated.
""",
    "primitives_api": API_INTRO
    + """
## Required Code Structure

### 1. build_agent(sandbox)
Build cantilever using get_build_zone(), get_structure_mass_limit(), get_structure_mass(). Return any beam body.
### 2. agent_action(sandbox, agent_body, step_count)
No per-step action required (purely structural).
"""
    + ADD_BEAM_01_4_EXOTIC
    + ADD_JOINT_GROUND_ANCHOR
    + GET_STRUCTURE_MASS
    + SET_MATERIAL_PROPERTIES_STATICS
    + GET_BUILD_ZONE
    + GET_STRUCTURE_MASS_LIMIT,
}
