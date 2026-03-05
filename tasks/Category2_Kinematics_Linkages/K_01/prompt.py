"""
K-01: The Walker task Prompt and Primitives definition
"""

import json
import os

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)


TASK_PROMPT = {
    'task_description': """
Design a 2D side-view walker that moves forward using motor-driven joints.

## Task Environment
- **Ground**: A flat horizontal surface at y=1.0m.
- **Build Zone**: x=[0, 50], y=[2, 10]. All structure components must be placed within this zone.
- **Starting Position**: Walker components should be centered around x=10m, y=4.5m for an initial drop.
- **Target**: Move the walker's torso to at least x=25.0m (15 meters forward from starting x).

## Constraints (must satisfy)
- **Stability**: The torso (main body) must always stay above y=1.2m. If the torso touches the ground or falls below y=1.2m, the task fails.
- **Motion**: The walker must maintain forward motion for at least 15.0 seconds.
- **Mass Budget**: Total structure mass must be less than 100 kg.
- **Build Zone**: All components must stay within x=[0, 50], y=[2, 10].
- **Beam Dimensions**: 0.05 <= width, height <= 5.0 meters.
- **Wheel Radius** (if used): 0.05 <= radius <= 0.8 meters.

## Instructions
1. **Design**: Create a walker structure (e.g., bipedal, quadrupedal, or using rotating linkages).
2. **Control**: Use `set_motor` on pivot joints in `agent_action` to drive the walker forward.
""",
    
    'success_criteria': """
## Success Criteria
1. **Movement**: Reaches x >= 25.0m.
2. **Stability**: Torso y > 1.2m at all times.
3. **Locomotion**: Maintains active motion for >= 15.0 seconds.

## Design Constraints
- **Mass Budget**: < 100 kg.
- **APIs**: Use only the primitives documented below.
""",
    
    'primitives_api': '\n\n'.join(_api_data['K_01'].values()),
}
