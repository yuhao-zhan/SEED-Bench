"""
S-01: The Bridge task Prompt and Primitives definition
"""

import json
import os

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)


TASK_PROMPT = {
    'task_description': """
Design a static bridge to connect two cliffs. A vehicle will spawn on the left cliff and attempt to cross to the right.

## Task Environment
- **Cliffs**: Two static platforms separated by a wide gap.
- **Left Cliff**: Ends at x=10.0m, y=10.0m.
- **Right Cliff**: Starts at x=25.0m, y=10.0m.
- **Vehicle**: A motorized vehicle will spawn on the left cliff and move right at a constant velocity.
- **Fail Zone**: A water surface exists at y=0m. If the vehicle or structural components fall into it, the task fails.
- **Target**: The vehicle must fully cross the gap and reach at least x=30.0m on the right side.

## Task Objective
Design a stable bridge structure that can:
1. Span the gap and connect the two cliffs.
2. Support the dynamic load of the heavy vehicle as it crosses.
3. Provide a continuous and smooth deck surface for the vehicle's wheels.
4. Maintain structural integrity under load. Joints have strength limits; excessive force or torque will cause them to break.

## Constraints (must satisfy)
- **Mass Budget**: Total structure mass must be less than 2000 kg.
- **Build Zone**: Structure must be built within x=[10, 25], y=[5, 15]. The deck surface may extend beyond these bounds to reach the target x=30.0m.
- **Beam Dimensions**: 0.1 <= width, height <= 10.0 meters.
- **Traction**: The deck surface must provide sufficient friction for the vehicle's wheels to roll without excessive slipping.
""",
    
    'success_criteria': """
## Success Criteria
1. **Passage**: Vehicle reaches x >= 30.0m.
2. **Integrity**: No structural breaks (all joints must remain intact during the crossing).
3. **Smoothness**: The vehicle's vertical acceleration must remain low (avoid bumpy or collapsing decks).

## Design Constraints
- **Mass Budget**: < 2000 kg.
- **APIs**: Use only the primitives documented below.
""",
    
    'primitives_api': '\n\n'.join(_api_data['S_01'].values()),
}
