"""
K-02: The Climber task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM,
    ADD_PAD,
    SET_PAD_ACTIVE,
    ADD_JOINT_PIVOT,
    ADD_JOINT_RIGID,
    SET_MOTOR,
    GET_STRUCTURE_MASS,
    SET_MATERIAL_PROPERTIES,
    JOINTS_LIST,
)

TASK_PROMPT = {
    'task_description': """
Design a 2D side-view mechanism that climbs a vertical wall using motors and suction pads.

## Task Environment
- **Wall**: Vertical wall surface at x=5.0m.
- **Ground**: Flat surface at y=1.0m.
- **Build Zone**: x=[0, 5], y=[0, 20]. All structure components must be placed within this zone.
- **Starting Position**: Climber components should be centered around x≈4.25m, y≈2.2m (below the target line).
- **Target (Red Line)**: Reach a height of y=3.5m (measured at the climber's torso).

## Constraints (must satisfy)
- **Wall Attachment**: The climber must never fall below y=1.0m and must stay near the wall (torso x in [3.0, 5.5]m).
- **Upward Motion**: The climber must show upward movement for at least 1.5 seconds.
- **Mass Budget**: Total structure mass must be less than 50 kg.
- **Suction Pads**: Adhesion pads are provided for wall attachment.
- **Beam Dimensions**: 0.05 <= width, height <= 3.0 meters.
- **Pad Radius**: 0.05 <= radius <= 0.25 meters.

## Instructions
1. **Stick to Wall**: Use `add_pad` and `set_pad_active(pad, True)` to create adhesion toward the vertical wall.
2. **Climb**: Use `set_motor` on pivot joints in `agent_action` to drive legs or wheels against the wall to push the climber upward.
""",
    
    'success_criteria': """
## Success Criteria
1. **Wall Attachment**: Stays on wall (y > 1.0m, x ∈ [3.0, 5.5]).
2. **Upward Motion**: Sustained upward movement for >= 1.5 seconds.
3. **Target Reached**: Torso reaches y >= 3.5m for a full score.

## Design Constraints
- **Mass Budget**: < 50 kg.
- **APIs**: Use only the primitives documented below.
""",
    
    'primitives_api': API_INTRO + ADD_PAD + SET_PAD_ACTIVE + ADD_BEAM + ADD_JOINT_PIVOT + ADD_JOINT_RIGID + SET_MOTOR + GET_STRUCTURE_MASS + SET_MATERIAL_PROPERTIES + JOINTS_LIST,
}
