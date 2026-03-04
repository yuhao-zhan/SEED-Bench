"""
F-06: The Pipeline (hard) task Prompt and Primitives definition
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
Design a transport system to route fluid particles to a narrow target zone while avoiding environmental hazards.

## Task Environment
- **Fluid**: A batch of 60 small fluid particles released from a source container.
- **Target Zone**: x in [18, 22] m, y in [0, 1.5] m.
- **Hazards**: Pits may exist in the corridor; particles entering them are lost.
- **Build Zone**: x=[6, 18] m, y=[0, 6] m.
- **Control**: You can apply forces directly to particles using `apply_force_to_particle()`.

## Task Objective
Design a system (structure and control) that:
1. Directs at least 90% of released fluid particles into the target zone.
2. Navigates particles safely over any pits or obstacles.
3. Operates within a per-step force budget and total structure mass limit.
""",
    "success_criteria": """
## Success Criteria
1. **Delivery Efficiency**: At least 90% of released particles reach the target zone.
2. **Resource Management**: Per-step force usage must not exceed the environment's budget.

## Design Constraints
- **Mass Budget**: Total structure mass <= 380 kg.
- **Force Budget**: 12000 N per step (nominal).
- **APIs**: Use only the primitives documented below.
""",
    "primitives_api": API_INTRO
    + ADD_BEAM
    + ADD_JOINT_RIGID
    + SET_MATERIAL_PROPERTIES
    + GET_FLUID_PARTICLES
    + APPLY_FORCE_TO_PARTICLE,
}
