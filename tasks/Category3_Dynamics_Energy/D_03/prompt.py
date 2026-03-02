"""
D-03: The Armored Vehicle task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM,
    ADD_JOINT_RIGID,
    GET_VEHICLE_CABIN,
)

TASK_PROMPT = {
    "task_description": """
Design armor for a vehicle cabin to protect it from falling debris.

## Task Environment
- **Vehicle Cabin**: A rectangular body that will move horizontally.
- **Debris**: Heavy blocks will fall from y=10.0m onto the vehicle path.
- **Build Zone**: Armor components must be attached to the vehicle cabin.
- **Target**: The vehicle cabin must reach x=30.0m with its structural integrity intact.

## Task Objective
Design armor that:
1. Absorbs or deflects the impact of falling debris.
2. Protects the main cabin from damage.
3. Does not hinder the vehicle's horizontal motion.
""",
    "success_criteria": """
## Success Criteria
1. **Reach**: Vehicle reaches x >= 30.0m.
2. **Integrity**: Cabin remains intact (no critical joint breaks or collisions).

## Design Constraints
- **Mass Budget**: Total armor mass < 1000 kg.
- **APIs**: Use only the primitives documented below.
""",
    "primitives_api": API_INTRO
    + GET_VEHICLE_CABIN
    + ADD_BEAM
    + ADD_JOINT_RIGID,
}
