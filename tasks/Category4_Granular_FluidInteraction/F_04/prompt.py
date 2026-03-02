"""
F-04: The Filter task Prompt and Primitives definition (feedback-driven variant)
"""
from ...primitives_api import (
    API_INTRO,
    ADD_STATIC_BEAM_08_1,
    GET_PARTICLES_MEDIUM,
    GET_PARTICLES_SMALL,
    GET_STRUCTURE_MASS,
    SET_MATERIAL_PROPERTIES_STATICS,
)

TASK_PROMPT = {
    "task_description": """
Design a filter that separates a mixture of **small**, **medium**, and **large** balls into three distinct spatial regions.

The environment has wind, obstacles, moving elements in the feed area, and particles released in waves. Zone boundaries, particle radii, and aperture specifications may need to be inferred from simulation feedback.

## Task Environment
- **Build Zone**: x=[5.22, 6.88], y=[1.72, 2.38]. All beams within this zone.
- **Max Beams**: At most 6 beams (bars).
- **Material Budget**: Total structure mass below limit (check sandbox.MAX_STRUCTURE_MASS).
""",
    "success_criteria": """
## Success Criteria
1. **Purity**: Classification purity meets the target (reported in feedback).
2. **Integrity**: The filter structure remains intact.

## Design Constraints
- **Build Zone**: x=[5.22, 6.88], y=[1.72, 2.38].
- **Beam limits**: 0.08 <= width, height <= 1.0 m.
- **Max Beams**: At most 6 beams.
- **Mass**: Below sandbox.MAX_STRUCTURE_MASS.
""",
    "primitives_api": API_INTRO
    + ADD_STATIC_BEAM_08_1
    + GET_STRUCTURE_MASS
    + SET_MATERIAL_PROPERTIES_STATICS
    + GET_PARTICLES_SMALL
    + GET_PARTICLES_MEDIUM,
}
