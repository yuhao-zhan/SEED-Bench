"""
K-03: The Gripper task Prompt and Primitives definition
"""

import json
import os

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)


TASK_PROMPT = {
    'task_description': """
Design a gripper mechanism that grasps an object and lifts it using motor rotation or slider motion.

## Task Environment
- **Gantry (Anchor)**: A static horizontal support at y=10.0m. You MUST attach your gripper base to this gantry using `get_anchor_for_gripper()`.
- **Object**: Located at x=5.0m, y=2.0m on a platform.
- **Platform**: The object rests on a platform below its starting height.
- **Build Zone**: x=[0, 10], y=[5, 15]. All structure components must be placed within this zone.
- **Target (Red Line)**: Lift the object to at least y=3.5m.

## Constraints (must satisfy)
- **Sustain**: Once reached, the object must be held at or above y=3.5m for at least 80 steps (~1.34 seconds).
- **Stability**: The object must not fall below y=1.9m after the lifting process has started.
- **Mass Budget**: Total structure mass must be less than 30 kg.
- **Build Zone**: All components must be within x=[0, 10], y=[5, 15].
- **Beam Dimensions**: 0.05 <= width, height <= 2.0 meters.

## Instructions
1. **Anchor Base**: Use `get_anchor_for_gripper()` to get the gantry body and weld your gripper base to it at y=10.0m.
2. **Grasp and Lift**: Design a mechanism (e.g., using `type='slider'` for vertical motion and `type='pivot'` for fingers) to reach down, grasp the object, and pull it up.
3. **Targeting**: Use `get_object_position()` to find the object's current coordinates.
""",
    
    'success_criteria': """
## Success Criteria
1. **Lifting**: Object reaches y >= 3.5m and sustains it for >= 80 steps.
2. **Stability**: No drops (stays above y=1.9m after lifting starts).

## Design Constraints
- **Mass Budget**: < 30 kg.
- **APIs**: Use only the primitives documented below.
""",
    
    'primitives_api': '\n\n'.join(_api_data['K_03'].values()),
}
