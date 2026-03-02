"""
F-01: The Dam task Prompt and Primitives definition (BRUTAL variant)
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM_DAM,
    ADD_JOINT_DAM_NO_ANCHOR,
    BODIES_LIST,
    GET_STRUCTURE_MASS,
    GET_TERRAIN_JOINT_COUNT,
    JOINTS_LIST,
    SET_MATERIAL_PROPERTIES_STATICS,
)

TASK_PROMPT = {
    "task_description": """
You need to design a dam to block water particles from flowing into the downstream area.

Build zones are **narrow strips** on the left, in the middle, and on the right of the gate. The dam must form **one connected structure** (all beams linked by joints) and keep leakage within the allowed limit. The environment includes moving boundaries, debris, and disturbances — your design must hold under load.

## Task Environment
- **Three strips**: Left x=[12.4, 12.6], middle x=[12.9, 13.1] (bridge), right x=[13.4, 13.6].
- **Moving downstream wall**, debris impacts, earthquake impulses.
- **Breakable joints**: Weld joints break if reaction force exceeds threshold.
""",
    "success_criteria": """
## Success Criteria
1. **Containment**: Leakage rate ≤ 0.1%.
2. **Integrity**: No broken joints (debris, earthquake, surges).
3. **Connectivity**: Dam is one connected structure; at least one beam in left strip, **at least one in middle strip x=[12.9,13.1]**, and at least one in right strip (two cross-joints required).

## Design Constraints
- **One connected component** using **all three strips**; middle strip at most 1 beam (bridge); at least one cross-joint left–middle and one middle–right.
- **Min 3 beam centers per band** y=[0.5,2.5], [2.5,5], [5,7.5].
- **Beam limits**: width ≤ 0.6 m, height ≤ 1.5 m; beam bottom (y - height/2) ≥ 0.5.
- **At most 11** beam-to-beam joints. **ZERO floor anchors** (get_terrain_joint_count must be 0).
- **Mass** < 380 kg. **At most 18 beams**; middle strip at most 1; right strip at most 2.
""",
    "primitives_api": API_INTRO
    + ADD_BEAM_DAM
    + ADD_JOINT_DAM_NO_ANCHOR
    + GET_STRUCTURE_MASS
    + GET_TERRAIN_JOINT_COUNT
    + SET_MATERIAL_PROPERTIES_STATICS
    + BODIES_LIST
    + JOINTS_LIST,
}
