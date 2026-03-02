"""
K-04: The Pusher task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM_05_3,
    ADD_WHEEL_05_08,
    ADD_JOINT_PIVOT,
    SET_MOTOR,
    GET_STRUCTURE_MASS,
    SET_MATERIAL_PROPERTIES_KINEMATICS,
    REMOVE_INITIAL_TEMPLATE,
    JOINTS_LIST,
)

TASK_PROMPT = {
    'task_description': """
Design a pusher mechanism that can push heavy objects forward along the ground using only motor rotation.

## Task Environment
- **Object**: Heavy object at x=8.0m (on ground). Mass 50 kg, size 1.0m × 0.8m.
- **Build Zone**: x=[0, 15], y=[1.0, 8]. All components must be placed within this zone. y=1.0 is ground top.
- **Starting Position**: Pusher spawns at approximately x=3m, y=2.5m (behind object).

## Constraints (must satisfy)
- **Build Zone**: All components within x=[0, 15], y=[1.0, 8].
- **Structure Mass**: Total mass < 40 kg.
- **Beam**: 0.05 <= width, height <= 3.0 (see API).
- **Wheel** (if used): 0.05 <= radius <= 0.8 (see API).
- **Object must remain on the ground** (pushing, not launching).
- **Remove template**: Call `remove_initial_template()` at the start of build_agent if available.

## Task Objective
Design a pusher that can:
1. Continuously contact and push the object forward along the ground
2. Push the object at least 8 meters (object x >= 16m)
3. Prevent tipping (pusher angle stays within ±30° from horizontal)
""",
    
    'success_criteria': """
## Success Criteria
1. **Pushing**: Object is pushed forward at least 8 meters (object x >= 16m).
2. **Stability**: Pusher never tips over (angle within ±30° from horizontal).
3. **Traction**: Pusher maintains forward motion (wheels maintain ground contact).

## Design Constraints
- **Build Zone**: x=[0, 15], y=[1.0, 8].
- **Mass Budget**: < 40 kg.
- **APIs**: Use only the primitives documented below. Do not access internal attributes.
""",
    
    'primitives_api': API_INTRO + REMOVE_INITIAL_TEMPLATE + ADD_BEAM_05_3 + ADD_WHEEL_05_08 + ADD_JOINT_PIVOT + SET_MOTOR + GET_STRUCTURE_MASS + SET_MATERIAL_PROPERTIES_KINEMATICS + JOINTS_LIST,
}
