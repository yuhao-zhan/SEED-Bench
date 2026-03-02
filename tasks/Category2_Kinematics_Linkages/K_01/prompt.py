"""
K-01: The Walker task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM_05_5,
    ADD_WHEEL_05_08,
    ADD_JOINT_PIVOT,
    SET_MOTOR,
    GET_STRUCTURE_MASS,
    SET_MATERIAL_PROPERTIES_KINEMATICS,
    JOINTS_LIST,
)

TASK_PROMPT = {
    'task_description': """
Design a 2D side-view walker that moves forward using only motor rotation.

## Task Environment
- **Ground**: Flat surface at y=1.0m.
- **Build Zone**: x=[0, 50], y=[2, 10]. All structure components must be placed within this zone.
- **Starting Position**: Walker spawns at approximately x=10m, y=3m.

## Constraints (must satisfy)
- **Build Zone**: All components within x=[0, 50], y=[2, 10].
- **Structure Mass**: Total mass < 100 kg.
- **Beam**: 0.05 <= width, height <= 5.0 (see API).
- **Wheel** (if used): 0.05 <= radius <= 0.8 (see API).

## Task Objective
Design a walker that can:
1. Move forward continuously using only motor-driven joints
2. Keep the torso above the ground (torso y > 1.5m)
3. Achieve stable forward locomotion
""",
    
    'success_criteria': """
## Success Criteria
1. **Movement**: Walker moves forward at least 10 meters from starting position.
2. **Stability**: Torso never touches the ground (torso y > 1.5m at all times).
3. **Locomotion**: Walker maintains forward motion for at least 5 seconds.

## Design Constraints
- **Build Zone**: x=[0, 50], y=[2, 10].
- **Mass Budget**: < 100 kg.
- **APIs**: Use only the primitives documented below. Do not access internal attributes.
""",
    
    'primitives_api': API_INTRO + ADD_BEAM_05_5 + ADD_WHEEL_05_08 + ADD_JOINT_PIVOT + SET_MOTOR + GET_STRUCTURE_MASS + SET_MATERIAL_PROPERTIES_KINEMATICS + JOINTS_LIST,
}
