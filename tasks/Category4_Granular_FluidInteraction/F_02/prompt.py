"""
F-02: The Amphibian task Prompt and Primitives definition
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
Design an amphibian vehicle to cross a body of water and reach the target bank.

## Task Environment
- **Water**: A 10m wide water gap between x=10m and x=20m.
- **Target**: Reach the right bank at x >= 26.0m.
- **Build Zone**: Vehicle hull is centered at x=15.0m, y=2.5m. Structure can be built in x=[13.5, 16.5], y=[2.5, 4.5].
- **Propulsion**: You can apply periodic thrust forces to your structure's components using `apply_force()`.

## Task Objective
Design a vehicle that:
1. Remains buoyant while crossing the water.
2. Uses effective propulsion (e.g., paddles) to move forward against currents and headwinds.
3. Reaches the target bank.
""",
    "success_criteria": """
## Success Criteria
1. **Goal Reach**: Vehicle front reaches x >= 26.0m.

## Design Constraints
- **Mass Budget**: Total structure mass <= 80 kg.
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
