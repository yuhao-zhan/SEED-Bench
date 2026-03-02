"""
K-06: The Wiper task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM_05_2,
    ADD_JOINT_PIVOT,
    SET_MOTOR,
    GET_STRUCTURE_MASS,
    SET_MATERIAL_PROPERTIES_KINEMATICS,
    WELD_TO_GLASS,
    REMOVE_INITIAL_TEMPLATE,
    JOINTS_LIST,
)

TASK_PROMPT = {
    'task_description': """
Design a wiper mechanism that can clean all particles from a glass surface using only motor rotation.

## Task Environment
- **Glass Surface**: Flat surface at y=2.0m, length 12m (x from 0 to 12).
- **Particles**: 45 particles randomly distributed on the glass. All must be removed (100% cleaning).
- **Build Zone**: x=[0, 12], y=[2, 10]. All components must be placed within this zone.
- **Starting Position**: Wiper spawns at approximately x=6m, y=4m.
- **Particle removal**: A particle is "removed" when pushed off the glass (x < 0.5 or x > 11.5 or |y - 2.0| >= 0.5).
- **Wiper–glass**: The wiper does not collide with the glass (it can swing through); it only collides with particles.

## Constraints (must satisfy)
- **Build Zone**: All components within x=[0, 12], y=[2, 10].
- **Structure Mass**: Total mass < 15 kg.
- **Beam**: 0.05 <= width, height <= 2.0 (see API).
- **Remove template**: Call `remove_initial_template()` at the start of build_agent if available.

## Task Objective
Design a wiper that can:
1. Sweep across the glass surface
2. Remove all 45 particles (100% cleaning)
3. Maintain motion for at least 12 seconds
""",
    
    'success_criteria': """
## Success Criteria
1. **Cleaning**: 100% of particles removed (residual = 0%).
2. **Coverage**: Every particle is reached and pushed off.
3. **Efficiency**: Wiper maintains motion for at least 12 seconds.

## Design Constraints
- **Build Zone**: x=[0, 12], y=[2, 10].
- **Mass Budget**: < 15 kg.
- **APIs**: Use only the primitives documented below. Do not access internal attributes.
""",
    
    'primitives_api': API_INTRO + REMOVE_INITIAL_TEMPLATE + ADD_BEAM_05_2 + ADD_JOINT_PIVOT + SET_MOTOR + GET_STRUCTURE_MASS + SET_MATERIAL_PROPERTIES_KINEMATICS + WELD_TO_GLASS + JOINTS_LIST,
}
