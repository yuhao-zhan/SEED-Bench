"""
S-05: The Shelter task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM,
    ADD_JOINT_RIGID,
    GET_STRUCTURE_MASS,
    SET_MATERIAL_PROPERTIES,
)

TASK_PROMPT = {
    'task_description': """
Protect a fragile Core (a square box at the origin) from heavy falling boulders that come from multiple directions.
Boulders will spawn above the core, mostly targeting the center, but some will fall from the left and right sides. The core is extremely delicate and will fail if subjected to significant impact forces.

## Task Environment
- **Core**: A 1x1m box centered at (0, 0.5). It fails if any single impact force exceeds its structural limit.
- **Ground**: A static surface at y=0.5. Your shelter must be supported by the ground outside the designated keep-out zone.
- **Boulders**: Numerous heavy meteors fall from a high altitude (y=20m). They target the center heavily, but also strike from the sides. You must design a structure to deflect or absorb these impacts.
- **Beam Dimensions**: 0.1 <= width, height <= 10.0 m. 

## Task Objective
Design a shelter structure that:
1. Effectively shields the core from impacts originating from the center, left, and right.
2. Deflects or absorbs the kinetic energy of heavy falling boulders so that the force reaching the core remains minimal.
3. Maintains structural stability under its own weight and during repeated impacts.
4. Complies with the total mass budget and height restrictions.

## Constraints (must satisfy)
- **Keep-Out Zone**: You cannot build any structural components within 1.3m of the core center (0,0).
- **Height Limit**: No part of the shelter may extend above y=4.5m. This is strictly enforced at build time.
- **Mass Budget**: Total structure mass must be less than 120 kg.
- **Structural Integrity**: The shelter must remain standing throughout the bombardment.
""",
    
    'success_criteria': """
## Success Criteria
1. **Protection**: The core survives the entire bombardment without exceeding its impact force threshold.
2. **Stability**: The shelter does not collapse under its own weight or the weight of the debris.

## Design Constraints
- **Keep-Out Zone**: Beam center distance to (0,0) must be >= 1.3m.
- **Mass Budget**: < 120 kg.
- **Height Limit**: No beam may extend above y=4.5m (center_y + max(width, height)/2 <= 4.5).
- **APIs**: Use only the primitives documented below.
""",
    
    'primitives_api': API_INTRO + ADD_BEAM + ADD_JOINT_RIGID + GET_STRUCTURE_MASS + SET_MATERIAL_PROPERTIES,
}
