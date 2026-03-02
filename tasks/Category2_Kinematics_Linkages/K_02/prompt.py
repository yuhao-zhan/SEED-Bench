"""
K-02: The Climber task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM_05_3,
    ADD_PAD,
    SET_PAD_ACTIVE,
    ADD_JOINT_PIVOT,
    SET_MOTOR,
    GET_STRUCTURE_MASS,
    SET_MATERIAL_PROPERTIES_KINEMATICS,
    JOINTS_LIST,
)

TASK_PROMPT = {
    'task_description': """
Design a 2D side-view mechanism that climbs a vertical wall using motors and suction pads.

## Task Environment
- **Wall**: Vertical wall at x=5.0m.
- **Ground**: y=1.0m.
- **Build Zone**: x=[0, 5], y=[0, 20]. All structure components must be placed within this zone.
- **Starting Position**: Climber spawns low, near the wall (e.g. x≈4.25m, y≈2.2m).
- **Target (red line)**: y=3.5m. Reaching it gives full score. Partial pass = wall attachment + upward motion.

## Constraints (must satisfy)
- **Build Zone**: All components within x=[0, 5], y=[0, 20].
- **Structure Mass**: Total mass < 50 kg. Each pad has max load ≈55 N when active — keep mass reasonable.
- **Beam**: 0.05 <= width, height <= 3.0 (see API).
- **Pad**: 0.05 <= radius <= 0.25 (see API).

## Task Objective
Design a mechanism that can:
1. Stay on the wall (don't fall below y=1.0m, torso x in [3, 5.5]m)
2. Show upward motion (≥1.5s)
3. Reach the red line (torso y ≥ 3.5m) for full marks
""",
    
    'success_criteria': """
## Success Criteria
1. **Wall attachment**: Climber never falls below y=1.0m and stays near the wall (torso x in [3, 5.5]m).
2. **Upward motion**: Climber shows upward movement for at least 1.5 seconds.
3. **Red line**: Reaching y=3.5m gives full score; partial pass = wall + upward motion.

## Design Constraints
- **Build Zone**: x=[0, 5], y=[0, 20].
- **Mass Budget**: < 50 kg.
- **APIs**: Use only the primitives documented below. Do not access internal attributes.
""",
    
    'primitives_api': API_INTRO + ADD_PAD + SET_PAD_ACTIVE + ADD_BEAM_05_3 + ADD_JOINT_PIVOT + SET_MOTOR + GET_STRUCTURE_MASS + SET_MATERIAL_PROPERTIES_KINEMATICS + JOINTS_LIST,
}
