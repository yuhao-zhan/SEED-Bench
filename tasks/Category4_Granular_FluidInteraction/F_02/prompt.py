"""
F-02: The Snowplow task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM,
    ADD_JOINT_RIGID,
    GET_STRUCTURE_MASS,
    SET_MATERIAL_PROPERTIES,
    GET_VEHICLE_FRONT_X,
    APPLY_FORCE,
    BODIES_LIST,
)

TASK_PROMPT = {
    "task_description": """
Design a snowplow attachment for a vehicle to clear granular snow from its path.

## Task Environment
- **Vehicle**: A motorized vehicle that moves forward.
- **Snow**: Numerous small granular particles on the ground.
- **Build Zone**: Snowplow must be attached to the front of the vehicle.
- **Target**: Clear at least 80% of the snow from the vehicle's path.

## Task Objective
Design a plow that:
1. Effectively pushes granular snow to the sides.
2. Maintains ground contact without excessive friction or snagging.
3. Does not break under the load of the snow.
""",
    "success_criteria": """
## Success Criteria
1. **Clearing**: > 80% of particles removed from the target path.
2. **Integrity**: Structure remains attached and intact.

## Design Constraints
- **Mass Budget**: Total plow mass < 100 kg.
- **APIs**: Use only the primitives documented below.
""",
    "primitives_api": API_INTRO
    + ADD_BEAM
    + ADD_JOINT_RIGID
    + SET_MATERIAL_PROPERTIES
    + GET_STRUCTURE_MASS
    + GET_VEHICLE_FRONT_X
    + APPLY_FORCE
    + BODIES_LIST,
}
