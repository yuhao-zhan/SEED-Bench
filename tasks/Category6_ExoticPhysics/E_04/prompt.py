"""
E-04: Variable Mass task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM,
    ADD_JOINT_RIGID,
    ADD_JOINT_PIVOT,
    GET_BUILD_ZONE,
    GET_GROUND_Y_TOP,
    GET_MIN_BEAMS,
    GET_MIN_JOINTS,
    GET_SPAN_BOUNDS,
    GET_STRUCTURE_MASS,
    GET_STRUCTURE_MASS_LIMIT,
)

TASK_PROMPT = {
    "task_description": """
Design a complex structure that remains intact under sinusoidally varying mass and environmental vibration.

## Task Environment
- **Mass Variation**: Every beam's mass varies over time according to multiple frequency components.
- **Base Excitation**: The ground support oscillates vertically and horizontally (elliptical vibration).
- **Fatigue**: Joint strength (force and torque limits) decays exponentially over time.
- **Build Zone**: x in [5.0, 15.0] m, y in [1.5, 8.0] m.
- **Goal**: Maintain structural integrity until the end of the simulation.

## Task Objective
Design a structure that:
1. Spans from x=6.0m to x=14.0m.
2. Uses at least 5 beams and 6 joints.
3. Includes at least one pivot (revolute) joint.
4. Withstands the varying inertial loads and base vibration without breaking any joints.
""",
    "success_criteria": """
## Success Criteria
1. **Integrity**: All joints remain intact throughout the simulation.
2. **Span**: Structure spans from at least x <= 6.0m to x >= 14.0m.
3. **Complexity**: Meets the minimum beam (5) and joint (6) counts.
4. **Variety**: At least one joint must be a pivot (`type='pivot'`).

## Design Constraints
- **Mass Budget**: Total structure mass (instantaneous) must remain within the limit (default 400 kg).
- **APIs**: Use only the primitives documented below.
""",
    "primitives_api": API_INTRO
    + GET_GROUND_Y_TOP
    + GET_BUILD_ZONE
    + GET_SPAN_BOUNDS
    + ADD_BEAM
    + ADD_JOINT_RIGID
    + ADD_JOINT_PIVOT
    + GET_STRUCTURE_MASS
    + GET_STRUCTURE_MASS_LIMIT
    + GET_MIN_BEAMS
    + GET_MIN_JOINTS,
}
