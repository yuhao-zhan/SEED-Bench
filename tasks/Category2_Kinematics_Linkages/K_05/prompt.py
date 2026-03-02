"""
K-05: The Lifter task Prompt and Primitives definition.
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM_05_4,
    ADD_JOINT_PIVOT,
    SET_MOTOR,
    GET_STRUCTURE_MASS,
    SET_MATERIAL_PROPERTIES_KINEMATICS,
    REMOVE_INITIAL_TEMPLATE,
    JOINTS_LIST,
)

TASK_PROMPT = {
    'task_description': """
Design a lift mechanism that can lift objects vertically to a specified height using only motor rotation.

## Task Environment
- **Object**: At x=4.0m, y=1.8m (on ground). Mass 20 kg, size 0.6m × 0.4m.
- **Build Zone**: x=[0, 8], y=[1, 12]. All components must be placed within this zone.
- **Object Start**: The object is always at ground (4m, 1.8m) when simulation starts. Your mechanism must physically lift it. Do not place the object on a pre-built high platform at build time.

## Constraints (must satisfy)
- **Build Zone**: All components within x=[0, 8], y=[1, 12].
- **Structure Mass**: Total mass < 60 kg.
- **Beam**: 0.05 <= width, height <= 4.0 (see API).
- **Remove template**: Call `remove_initial_template()` at the start of build_agent if available.

## Task Objective
Design a lift mechanism that can:
1. Lift the object vertically from ground to at least y=9m
2. Sustain the object at y>=9m for at least 3 seconds (180 steps) without the object sliding down (vertical velocity >= -0.4 m/s)
3. Keep structure intact (no joints break)
""",
    
    'success_criteria': """
## Success Criteria
1. **Lifting**: Object is lifted to height y >= 9m.
2. **Stability**: Lifter structure remains intact (no joints break).
3. **Sustain**: Object maintains y>=9m for at least 3 seconds. Sustain counts only when object is not sliding down (velocity_y >= -0.4 m/s).

## Design Constraints
- **Build Zone**: x=[0, 8], y=[1, 12].
- **Mass Budget**: < 60 kg.
- **APIs**: Use only the primitives documented below. Do not access internal attributes.
""",
    
    'primitives_api': API_INTRO + REMOVE_INITIAL_TEMPLATE + ADD_BEAM_05_4 + ADD_JOINT_PIVOT + SET_MOTOR + GET_STRUCTURE_MASS + SET_MATERIAL_PROPERTIES_KINEMATICS + JOINTS_LIST,
}
