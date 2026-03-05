"""
S-05: The Shelter task Prompt and Primitives definition
"""

import json
import os

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)


TASK_PROMPT = {
    'task_description': """
Protect a fragile Core (a sensitive circular object at x=10.0, y=1.0) from heavy falling boulders that come from multiple directions.
Boulders will spawn above the core, mostly targeting the center, but some will fall from the left and right sides. The core is extremely delicate and will fail if subjected to significant impact forces.

## Task Environment
- **Core**: A circular object centered at (10.0, 1.0). It fails if any single impact force exceeds its structural limit.
- **Ground**: A static surface at y=0.0. Your shelter must be supported by the ground outside the designated keep-out zone.
- **Boulders**: 12 boulders fall from a high altitude (y=15m). They target the build zone broadly. You must design a structure to deflect or absorb these impacts.
- **Beam Dimensions**: 0.1 <= width, height <= 10.0 m. 

## Task Objective
Design a shelter structure that:
1. Effectively shields the core from impacts originating from above.
2. Deflects or absorbs the kinetic energy of heavy falling boulders so that the force reaching the core remains minimal (< 150.0N).
3. Maintains structural stability under its own weight and during repeated impacts.
4. Complies with the total mass budget and height restrictions.

## Constraints (must satisfy)
- **Keep-Out Zone**: You cannot build any structural components within 1.3m of the core center (10.0, 1.0).
- **Height Limit**: No part of the shelter may extend above y=7.5m. This is strictly enforced at build time.
- **Mass Budget**: Total structure mass must be less than 300.0 kg.
- **Structural Integrity**: The shelter must remain standing throughout the bombardment.
""",
    
    'success_criteria': """
## Success Criteria
1. **Protection**: The core survives the entire bombardment without exceeding its 150.0N impact force threshold.
2. **Stability**: The shelter does not collapse under its own weight or the weight of the debris.

## Design Constraints
- **Keep-Out Zone**: Beam center distance to (10.0, 1.0) must be >= 1.3m.
- **Mass Budget**: < 300.0 kg.
- **Height Limit**: No beam may extend above y=7.5m.
- **APIs**: Use only the primitives documented below.
""",
    
    'primitives_api': '\n\n'.join(_api_data['S_05'].values()),
}
