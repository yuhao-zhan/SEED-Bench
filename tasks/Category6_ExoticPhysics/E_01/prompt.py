"""
E-01: Inverted Gravity task prompt.
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM_01_5,
    ADD_JOINT_TERRAIN_ANCHOR,
    GET_STRUCTURE_MASS,
    SET_MATERIAL_PROPERTIES_STATICS,
    GET_ARENA_BOUNDS,
    GET_BUILD_ZONE,
)

TASK_PROMPT = {
    "task_description": """
You need to design a structure that remains within a bounded arena where gravity is exotic:
gravity direction can be inverted or time-varying (e.g. oscillating between downward and upward).

## Task Environment
- **Arena**: Bounded box x in [0, 40], y in [0, 20]. Any body leaving fails.
- **Gravity**: Time-varying. It oscillates between downward and upward with a fixed period. What was "grip" can become "pull" toward the ceiling. Adapt so nothing flies out.
- **Obstacles**: Static obstacles in the arena at multiple heights. Any part of your structure intersecting an obstacle will collide; design to avoid every obstacle.
- **Forbidden zones**: Some regions disallow beam centers (rule-only). If any beam center lies in any forbidden zone, the run fails. Infer forbidden regions from feedback (forbidden_zone_violation, forbidden_offending).
- **Fail condition**: Any part leaving the arena boundary fails. Structure must remain intact (joints must not break). No beam center may lie in a forbidden zone.

## Constraints
- **Build zone**: x in [12, 28], y in [6, 18]. Beam centers must lie within this region.
- **Beam limits**: 0.1 ≤ width, height ≤ 5.0 m.
- **Material budget**: Total structure mass ≤ 200 kg.
- **Beam count**: At most 12 beams.
- **Anchors**: Use add_joint(body_a, None, anchor_point, type='rigid') to anchor to floor (anchor y near 0), ceiling (anchor y near 20), or walls. Use get_arena_bounds() for (x_min, x_max, y_min, y_max); use y_min for floor anchor, y_max for ceiling anchor.

You may ONLY use the APIs documented below. Do not access internal attributes.
""",
    "success_criteria": """
## Success Criteria
1. **In bounds**: No body of your structure has position outside the arena during the evaluation period.
2. **Structure intact**: Joints remain intact (no structural failure).
3. **No persistent collision**: Structure must not be blocked or pushed out by obstacles.

## Required Code Structure

### 1. build_agent(sandbox)
Build a structure within the build zone. Use get_arena_bounds() for anchor points. Return any beam body.
### 2. agent_action(sandbox, agent_body, step_count)
No per-step control needed; structure is purely passive.
""",
    "primitives_api": API_INTRO
    + ADD_BEAM_01_5
    + ADD_JOINT_TERRAIN_ANCHOR
    + GET_STRUCTURE_MASS
    + SET_MATERIAL_PROPERTIES_STATICS
    + GET_ARENA_BOUNDS
    + GET_BUILD_ZONE,
}
