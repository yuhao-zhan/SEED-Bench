"""
F-03: The Excavator — task prompt (per user TASK_F03 spec).
"""
from ...primitives_api import (
    API_INTRO,
    ADD_ANCHORED_BASE,
    ADD_BEAM_01_15,
    ADD_REVOLUTE_JOINT,
    ADD_SCOOP,
    BODIES_LIST,
    GET_STRUCTURE_MASS,
    HAS_CENTRAL_WALL,
    SET_MATERIAL_PROPERTIES_STATICS,
)

TASK_PROMPT = {
    "task_description": """
Dig "sand" particles from a pit and transport them into a hopper/truck.
You need a bucket/scoop design that can hold material without spilling during rotation.

## Environment
- **The Pit**: x=[0, 5], filled with 200 sand particles (High Friction). Particles drift toward +x (simulated slope/conveyor); scoop quickly or they move away.
- **Central Wall**: Optional vertical obstacle at x=0 from y=0 to y=2.2. The arm cannot swing directly from pit to hopper—it will collide. You must lift the arm high first (so it clears y=2.2 when crossing x=0), then swing toward the hopper; on return, swing high first then lower into the pit. Use `has_central_wall()` to check.
- **The Hopper**: Target container at x=-5, y=3. Only particles landing in the **center region** (x in [-5.5, -4.5], y in [2.5, 3.5]) count; dump accurately.
- **Agent**: Fixed base at x=-2, y=0. Arm reach required. Scoop has limited carry capacity per trip.

## Design Constraints
- **Base**: Fixed anchor at x=-2, y=0 (use add_anchored_base).
- **Mechanism**: Must have at least 2 degrees of freedom (Arm + Bucket).
- **Build Zone**: x=[-4, 2], y=[0, 5]. Mass < 800 kg.
- **Spillage**: Spilled sand is lost.
""",
    "environment_specs": """
- **The Pit**: x=[0, 5], 200 sand particles; pit drift (force toward +x).
- **Central Wall**: x=0, y in [0, 2.2] — arm must clear it (lift high before swinging). Check with has_central_wall().
- **The Hopper**: x=-5, y=3; valid count zone x=[-5.5, -4.5], y=[2.5, 3.5].
- **Agent**: Fixed base at x=-2, y=0.
""",
    "design_constraints": """
- **Base**: Fixed anchor at x=-2, y=0.
- **Mechanism**: Must have at least 2 degrees of freedom (Arm + Bucket).
- **Spillage**: Spilled sand is lost.
- **Store joints**: After add_revolute_joint, set sandbox.agent_arm_joint = arm_joint and sandbox.agent_bucket_joint = bucket_joint for use in agent_action.
""",
    "success_criteria": """
1. **Collection**: Successfully deposit > 50 sand particles into the hopper (valid zone may be full hopper or stricter center region).
2. **Efficiency**: Complete within 40 seconds.
3. **Obstacles**: Pit drift may push particles; optional central wall may require lifting arm to clear before swinging.
""",
    "primitives_api": API_INTRO
    + ADD_BEAM_01_15
    + ADD_ANCHORED_BASE
    + ADD_REVOLUTE_JOINT
    + ADD_SCOOP
    + GET_STRUCTURE_MASS
    + SET_MATERIAL_PROPERTIES_STATICS
    + HAS_CENTRAL_WALL
    + BODIES_LIST,
}
