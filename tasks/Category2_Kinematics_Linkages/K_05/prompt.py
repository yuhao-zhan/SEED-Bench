"""
K-05: The Lifter task Prompt and Primitives definition
"""

import json
import os

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)


TASK_PROMPT = {
    'task_description': """
Design a lift mechanism that can lift an object vertically from the ground to a specified height using only motor rotation.

## Task Environment
- **Ground**: Flat surface at y=1.0m.
- **Object**: Located at x=4.0m, y=1.8m (resting on the ground).
- **Build Zone**: x=[0, 8], y=[1, 12]. All structure components must be placed within this zone.
- **Target (Red Line)**: Lift the object to at least y=9.0m (8.0 meters above the ground).

## Constraints (must satisfy)
- **Sustain**: Once reached, the object must be held at or above y=9.0m for at least 3.0 seconds. The sustain count only increments when the object is NOT sliding down (vertical velocity >= -0.4 m/s).
- **Integrity**: The lifter structure must remain intact; the task fails if any joints break under the load.
- **Mass Budget**: Total structure mass must be less than 60 kg.
- **Build Zone**: All components must be within x=[0, 8], y=[1, 12].
- **Beam Dimensions**: 0.05 <= width, height <= 4.0 meters.

## Instructions
1. **Design**: Create a lifting structure (e.g., a scissor lift or an arm) that starts below or around the object and moves it upward.
2. **Control**: Use `set_motor` on pivot joints in `agent_action` to drive the lifting motion and maintain the target height.
""",
    
    'success_criteria': """
## Success Criteria
1. **Lifting**: Reaches y >= 9.0m.
2. **Sustain**: Holds the object at target for >= 3.0 seconds (velocity_y >= -0.4 m/s).
3. **Integrity**: Structure remains intact (no joint breaks).

## Design Constraints
- **Mass Budget**: < 60 kg.
- **APIs**: Use only the primitives documented below.
""",
    
    'primitives_api': '\n\n'.join(_api_data['K_05'].values()),
}
