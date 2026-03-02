"""
S-05: The Shelter task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM_01_10,
    ADD_JOINT_STATICS,
    GET_STRUCTURE_MASS,
    SET_MATERIAL_PROPERTIES_STATICS,
)

TASK_PROMPT = {
    'task_description': """
Protect a fragile Core (1x1m box at origin) from falling boulders that come from BOTH sides and mostly from the CENTER.
Meteors spawn from the left (x in [-5,-2]), right (x in [2,5]), and two out of every three from the CENTER (x in [-2,2]) so the core is heavily targeted. The core fails if any single impact force exceeds 14N.

## Task Environment
- **Core**: 1x1m box centered at (0, 0.5). Fails if any impact force > 14N.
- **Ground**: Static ground, top at y=0.5. Structure must be supported by the ground (outside keep-out zone).
- **Meteors**: 28 boulders (260kg each, radius 0.5m) fall from y=20m. Spawn pattern: CENTER, CENTER, left/right, repeat (19 of 28 are center hits). You must deflect or absorb impacts from all directions with very little force reaching the core.
- **Beam Limits**: 0.1 <= width, height <= 10.0 m. Cannot build within 1.3m of core center (0,0). No beam may extend above y=4.5m (enforced at build time). The check uses a conservative bound: for each beam, center_y + max(width, height)/2 must be <= 4.5 (so any orientation of the beam stays within limit).

## Task Objective
Design a shelter structure that:
1. Protects the core from impact from BOTH sides and from CENTER (most impacts are directly above)
2. Deflects or absorbs 260kg meteor energy so that core never sees >14N
3. Remains stable under its own weight
4. Stays within the mass budget (120kg) and never exceeds y=4.5m
""",
    
    'success_criteria': """
## Success Criteria
1. **Protection**: No single impact on the core may exceed 14N. (Max force on core must stay < 14N.)
2. **Stability**: Shelter does not collapse under its own weight.

## Design Constraints
- **Keep-Out Zone**: Cannot build within 1.3m of the Core center (0,0). Beam center distance to (0,0) must be >= 1.3m.
- **Budget**: Max mass 120kg. Meteors are 260kg each.
- **Height Limit**: No beam may extend above y=4.5m (enforced at build time). Enforcement: center_y + max(width, height)/2 <= 4.5 for every beam.
""",
    
    'primitives_api': API_INTRO + ADD_BEAM_01_10 + ADD_JOINT_STATICS + GET_STRUCTURE_MASS + SET_MATERIAL_PROPERTIES_STATICS,
}
