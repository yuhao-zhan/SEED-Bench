"""
K-03: The Gripper task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM_05_2,
    ADD_JOINT_PIVOT,
    ADD_JOINT_SLIDER,
    SET_MOTOR,
    SET_SLIDER_MOTOR,
    GET_STRUCTURE_MASS,
    SET_MATERIAL_PROPERTIES_KINEMATICS,
    GET_ANCHOR_FOR_GRIPPER,
    GET_OBJECT_CONTACT_COUNT,
    REMOVE_INITIAL_TEMPLATE,
    JOINTS_LIST,
)

TASK_PROMPT = {
    'task_description': """
Design a gripper mechanism that grasps the object and lifts it using only motor rotation.

## Task Environment
- **Gantry (Anchor)**: Static support at y=10m. Attach your gripper base to it (use get_anchor_for_gripper) so the gripper does not fall.
- **Object**: At x=5.0m, y=2.0m (on a platform).
- **Build Zone**: x=[0, 10], y=[5, 15]. All gripper components must be built within this zone.

## Constraints (must satisfy)
- **Build Zone**: All components within x=[0, 10], y=[5, 15].
- **Structure Mass**: Total mass < 30 kg.
- **Beam**: 0.05 <= width, height <= 2.0 (see API).
- **Remove template**: Call `remove_initial_template()` at the start of build_agent if available.

## Task Objective
Design a gripper that can:
1. Attach base to the gantry anchor (rigid joint)
2. Reach the object, grasp it, and lift it
3. Lift the object to at least y=3.5m and sustain that height for ~80 steps without dropping
""",
    
    'success_criteria': """
## Success Criteria
1. **Grasping**: Gripper successfully grasps the object (at least one gripper body in contact).
2. **Lifting**: Object is lifted to height y >= 3.5m and sustained for at least ~80 steps.
3. **Stability**: Object never falls below y=1.9m after being lifted.

## Design Constraints
- **Build Zone**: x=[0, 10], y=[5, 15].
- **Mass Budget**: < 30 kg.
- **APIs**: Use only the primitives documented below. Do not access internal attributes.
""",
    
    'primitives_api': API_INTRO + REMOVE_INITIAL_TEMPLATE + ADD_BEAM_05_2 + ADD_JOINT_PIVOT + ADD_JOINT_SLIDER + SET_MOTOR + SET_SLIDER_MOTOR + GET_STRUCTURE_MASS + SET_MATERIAL_PROPERTIES_KINEMATICS + GET_ANCHOR_FOR_GRIPPER + GET_OBJECT_CONTACT_COUNT + JOINTS_LIST,
}
