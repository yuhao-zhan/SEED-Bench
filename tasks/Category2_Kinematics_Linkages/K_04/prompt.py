"""
K-04: The Pusher task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM,
    ADD_WHEEL,
    ADD_JOINT_RIGID,
    ADD_JOINT_PIVOT,
    SET_MOTOR,
    SET_MATERIAL_PROPERTIES,
    SET_FIXED_ROTATION,
    JOINTS_LIST,
)

TASK_PROMPT = {
    'task_description': """
Design a pusher mechanism that can push a heavy object forward along high-friction ground using motor rotation.

## Task Environment
- **Ground**: Flat surface at y=1.0m.
- **Object**: A heavy box at x=8.0m.
- **Build Zone**: x=[0, 15], y=[1.5, 8.0]. All structure components must be placed within this zone.
- **Starting Position**: Pusher components should be centered around x≈3.0m, y≈2.5m (behind the object).
- **Target**: Push the object forward at least 10.0 meters.

## Constraints (must satisfy)
- **Stability**: The pusher must not tip over. Its tilt angle must stay within ±30 degrees from horizontal (radians: [-π/6, π/6]).
- **Traction**: The pusher must maintain ground contact and forward motion. Avoid excessive wheel spinning or lifting wheels off the ground.
- **Mass Budget**: Total structure mass must be less than 40 kg.
- **Build Zone**: All components must be within x=[0, 15], y=[1.5, 8.0].
- **Beam Dimensions**: 0.05 <= width, height <= 3.0 meters.
- **Wheel Radius** (if used): 0.05 <= radius <= 0.8 meters.

## Instructions
1. **Design**: Create a stable, low-center-of-gravity chassis with wheels or legs.
2. **Control**: Use `set_motor` on pivot joints in `agent_action` to drive the pusher forward and push the object.
3. **Stability**: Use `set_fixed_rotation()` if needed to prevent the chassis from tipping.
""",
    
    'success_criteria': """
## Success Criteria
1. **Pushing**: Object reaches x >= 18.0m.
2. **Stability**: Pusher tilt angle stays within ±30°.
3. **Locomotion**: Sustained forward progress (no excessive wheel spinning or lifting).

## Design Constraints
- **Mass Budget**: < 40 kg.
- **APIs**: Use only the primitives documented below.
""",
    
    'primitives_api': API_INTRO + ADD_BEAM + ADD_WHEEL + ADD_JOINT_RIGID + ADD_JOINT_PIVOT + SET_MOTOR + SET_MATERIAL_PROPERTIES + SET_FIXED_ROTATION + JOINTS_LIST,
}
