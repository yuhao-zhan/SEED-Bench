"""
F-04: The Filter (Three-way) task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_STATIC_BEAM,
    GET_PARTICLES_SMALL,
    GET_PARTICLES_MEDIUM,
    GET_PARTICLES_LARGE,
    GET_STRUCTURE_MASS,
    SET_MATERIAL_PROPERTIES,
)

TASK_PROMPT = {
    "task_description": """
Design a static filtering structure to separate fluid particles into three size categories.

## Task Environment
- **Particles**: A mixture of small (radius ~0.06m), medium (radius ~0.10m), and large (radius ~0.14m) particles will fall through the structure.
- **Obstacles**: Static vertical baffles and moving horizontal sweepers in the feed zone will disturb particle flow.
- **Build Zone**: x=[5.22, 6.88] m, y=[1.72, 2.38] m.
- **Target Zones**: 
  1. Small particles should be directed to the bottom (y < 1.92m).
  2. Medium particles should be directed to the middle (1.92m <= y < 2.52m).
  3. Large particles should be retained in the upper zone (y >= 2.52m).

## Task Objective
Design a multi-layered filter that:
1. Effectively separates particles by size into their respective target zones.
2. Minimizes cross-contamination between categories.
3. Maintains structural stability under particle load and sweeper impact using only static beams.
""",
    "success_criteria": """
## Success Criteria
1. **Classification Purity**: Overall purity (correctly categorized particles / total particles) >= 35%.
2. **Integrity**: Structure remains stable and intact.

## Design Constraints
- **Mass Budget**: Total structure mass <= 75 kg.
- **Beam Limit**: Maximum 6 beams.
- **APIs**: Use only the primitives documented below.
""",
    "primitives_api": API_INTRO
    + ADD_STATIC_BEAM
    + SET_MATERIAL_PROPERTIES
    + GET_STRUCTURE_MASS
    + GET_PARTICLES_SMALL
    + GET_PARTICLES_MEDIUM
    + GET_PARTICLES_LARGE,
}
