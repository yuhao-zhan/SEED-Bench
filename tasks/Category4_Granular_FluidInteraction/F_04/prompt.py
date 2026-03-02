"""
F-04: The Sieve task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_STATIC_BEAM,
    GET_PARTICLES_MEDIUM,
    GET_PARTICLES_SMALL,
    GET_STRUCTURE_MASS,
    SET_MATERIAL_PROPERTIES,
)

TASK_PROMPT = {
    "task_description": """
Design a static sieve structure to separate different sizes of granular particles.

## Task Environment
- **Particles**: A mixture of small and medium particles will fall through the sieve.
- **Build Zone**: x=[5, 15] m, y=[2, 8] m.
- **Target**: Allow small particles to pass through while retaining medium particles.

## Task Objective
Design a sieve that:
1. Effectively filters small particles from medium ones.
2. Minimizes clogging or structural failure.
3. Uses static components for durability.
""",
    "success_criteria": """
## Success Criteria
1. **Sifting**: High percentage of small particles passed through, medium particles retained.
2. **Integrity**: Structure remains stable and intact.

## Design Constraints
- **Mass Budget**: Total structure mass < 200 kg.
- **APIs**: Use only the primitives documented below.
""",
    "primitives_api": API_INTRO
    + ADD_STATIC_BEAM
    + SET_MATERIAL_PROPERTIES
    + GET_STRUCTURE_MASS
    + GET_PARTICLES_SMALL
    + GET_PARTICLES_MEDIUM,
}
