"""
F-05: The Boat task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM,
    ADD_JOINT_RIGID,
    GET_STRUCTURE_MASS,
    SET_MATERIAL_PROPERTIES,
    BODIES_LIST,
)

TASK_PROMPT = {
    "task_description": """
Design a stabilization and containment structure for a boat in rough water.

## Task Environment
- **Boat**: A platform floating in water (x around 15m, y around 2.5m).
- **Cargo**: 10 granular particles loaded onto the boat.
- **Obstacles**: Static rocks are present in the water which can strike the boat or cargo.
- **Dynamic Forces**: The boat is subject to multi-mode waves, sudden gusts, lateral wind, and water currents.
- **Build Zone**: Structure must be attached to the boat body within x=[12.0, 18.0], y=[2.0, 4.5].

## Task Objective
Design a structure that:
1. Prevents all cargo from falling overboard despite severe vessel motion.
2. Lowers the center of mass or provides stabilization to prevent the boat from capsizing.
3. Withstands the impact of periodic rogue waves and lateral impulses.
""",
    "success_criteria": """
## Success Criteria
1. **Cargo Retention**: All initial cargo (100%) remains on the boat.
2. **Stability**: Boat does not capsize (angle must remain below 18 degrees).

## Design Constraints
- **Mass Budget**: Total structure mass <= 60 kg.
- **APIs**: Use only the primitives documented below.
""",
    "primitives_api": API_INTRO
    + ADD_BEAM
    + ADD_JOINT_RIGID
    + SET_MATERIAL_PROPERTIES
    + GET_STRUCTURE_MASS
    + BODIES_LIST,
}
