"""
F-06: The Pipeline task Prompt and Primitives definition (VERY HARD variant)
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM_01_12,
    ADD_JOINT_GROUND_ANCHOR,
    APPLY_FORCE_TO_PARTICLE,
    GET_FLUID_PARTICLES,
    GET_STRUCTURE_MASS,
    SET_MATERIAL_PROPERTIES_STATICS,
)

TASK_PROMPT = {
    "task_description": """
You need to design a pipeline or pump mechanism that transports fluid particles from a low source to a **target** through a hostile environment with **pits**, **time-varying headwind**, and a **strict per-step force budget**.

## Task Environment
- **Source**: Fluid particles start in x=[2, 6]m, y=[0, 1.5]m.
- **Target**: Zone defined by environment (check sandbox.TARGET_X_MIN/MAX, TARGET_Y_MIN/MAX). Particles inside count as delivered.
- **Build Zone**: x=[6, 18], y=[0, 6]. **Floor**: y=0.

## HOSTILE OBSTACLES
1. **Pits**: Multiple pits — particles entering are **LOST**. Route above pit y_max when in pit x range.
2. **HEADWIND (time-varying)**: For y>3m, headwind pushes **negative x**; magnitude oscillates.
3. **GRAVITY WELL**: In x=[10, 14], y=[1.5, 3.5], extra **downward** force. Push harder to lift through.
4. **FORCE BUDGET**: Total force magnitude per step is **capped** (sandbox.FORCE_BUDGET_PER_STEP, e.g. 8000–12000 N). Use `apply_force_to_particle(particle, fx, fy)`; the sandbox enforces the cap. **Prioritize** which particles to push.
""",
    "success_criteria": """
## Success Criteria
1. **Delivery**: Meet minimum delivery ratio (particles in target / initial).
2. **Integrity**: Structure remains intact (joints do not break).

## Design Constraints
- **Build Zone**: x=[6, 18], y=[0, 6]. **Mass**: < 380 kg.
- **Beam limits**: 0.1 <= width, height <= 1.2 m.
- **Force**: Use `sandbox.apply_force_to_particle(particle, fx, fy)` only. Per-step budget enforced. Use `sandbox.get_fluid_particles()` to get particles for control.
""",
    "primitives_api": API_INTRO
    + ADD_BEAM_01_12
    + ADD_JOINT_GROUND_ANCHOR
    + GET_STRUCTURE_MASS
    + SET_MATERIAL_PROPERTIES_STATICS
    + GET_FLUID_PARTICLES
    + APPLY_FORCE_TO_PARTICLE,
}
