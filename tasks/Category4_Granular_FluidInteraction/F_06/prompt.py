"""
F-06: The Fountain task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM,
    ADD_JOINT_RIGID,
    APPLY_FORCE_TO_PARTICLE,
    GET_FLUID_PARTICLES,
    SET_MATERIAL_PROPERTIES,
)

TASK_PROMPT = {
    "task_description": """
Design a fountain nozzle and control system to direct fluid particles into a target area.

## Task Environment
- **Fluid**: Continuous stream of small fluid particles.
- **Target Area**: x in [15, 20] m, y in [5, 10] m.
- **Build Zone**: x=[5, 10] m, y=[0, 5] m.

## Task Objective
Design a system that:
1. Directs fluid particles toward the target area using physical structures or forces.
2. Maintains a steady flow of particles into the target.
3. Stays within mass and beam count limits.
""",
    "success_criteria": """
## Success Criteria
1. **Target Accuracy**: High percentage of fluid particles entering the target area.
2. **Sustained Flow**: Continuous delivery of particles over time.

## Design Constraints
- **Mass Budget**: Total structure mass < 100 kg.
- **APIs**: Use only the primitives documented below.
""",
    "primitives_api": API_INTRO
    + ADD_BEAM
    + ADD_JOINT_RIGID
    + SET_MATERIAL_PROPERTIES
    + GET_FLUID_PARTICLES
    + APPLY_FORCE_TO_PARTICLE,
}
