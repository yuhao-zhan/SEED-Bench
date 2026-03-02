"""
K-06: The Wiper task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM,
    ADD_JOINT_PIVOT,
    ADD_JOINT_RIGID,
    SET_MOTOR,
    GET_STRUCTURE_MASS,
    SET_MATERIAL_PROPERTIES,
    SET_AWAKE,
    WELD_TO_GLASS,
    JOINTS_LIST,
)

TASK_PROMPT = {
    'task_description': """
Design a wiper mechanism that can clean all particles from a glass surface using motor rotation.

## Task Environment
- **Glass Surface**: Flat surface at y=2.0m, length 12m (x from 0 to 12).
- **Particles**: Numerous particles are randomly distributed on the glass.
- **Particle Removal**: A particle is considered "removed" when pushed off the glass surface boundaries.
- **Build Zone**: x=[0, 12], y=[2, 10]. All structure components must be placed within this zone.
- **Wiper–Glass**: The wiper does NOT collide with the glass surface itself; it only collides with the particles.

## Constraints (must satisfy)
- **Cleaning**: 100% of particles must be removed (residual = 0%).
- **Motion**: The wiper must maintain active movement for at least 12.0 seconds.
- **Mass Budget**: Total structure mass must be less than 15 kg.
- **Build Zone**: All components must be within x=[0, 12], y=[2, 10].
- **Beam Dimensions**: 0.05 <= width, height <= 2.0 meters.

## Instructions
1. **Anchor Base**: Use `weld_to_glass(body, anchor_point)` to fix your wiper's base relative to the glass surface.
2. **Sweep**: Design a sweeping mechanism to cover the entire width of the glass.
3. **Control**: Use `set_motor` on pivot joints in `agent_action` to drive the sweeping motion.
""",
    
    'success_criteria': """
## Success Criteria
1. **Cleaning**: 100% of particles removed (residual = 0%).
2. **Locomotion**: Sustained sweeping motion for >= 12.0 seconds.
3. **Stability**: Structure remains within build zone and mass limits.

## Design Constraints
- **Mass Budget**: < 15 kg.
- **APIs**: Use only the primitives documented below.
""",
    
    'primitives_api': API_INTRO + WELD_TO_GLASS + ADD_BEAM + ADD_JOINT_PIVOT + ADD_JOINT_RIGID + SET_MOTOR + GET_STRUCTURE_MASS + SET_MATERIAL_PROPERTIES + SET_AWAKE + JOINTS_LIST,
}
