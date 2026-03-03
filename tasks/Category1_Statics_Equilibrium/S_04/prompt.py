"""
S-04: The Balancer task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM,
    ADD_JOINT_RIGID,
    GET_STRUCTURE_MASS,
    ACCESS_TERRAIN_BODIES,
)

TASK_PROMPT = {
    'task_description': """
Build a structure on a sharp pivot at (0,0) that balances an asymmetric heavy load.
The goal is to design a system that maintains a level orientation despite the unbalanced weight and potential environmental disturbances.

## Task Environment
- **Pivot**: A sharp static support at (0,0).
- **The Load**: A heavy block located at or near x=3.0. It may automatically attach (weld) to your structure if any part of your design is built within 0.5m of (3,0), OR it may be DROPPED from above. If the load is not caught or falls, the task fails.
- **Environmental Anomalies**: The environment may contain static obstacles you must build around, or experience severe lateral wind forces that apply continuous torque to your structure.
- **Beam Dimensions**: 0.1 <= width <= 7.0 m, 0.1 <= height <= 2.0 m.

## Task Objective
Design a balanced structure that:
1. Extends to x=3.0 to successfully "catch" and support the heavy load.
2. Connects to the pivot point at (0,0).
3. Maintains a level orientation (horizontal angle within ±10 degrees) for 15 seconds. 
4. The structure must be free to rotate about the pivot; it must rely on active or passive mass balancing, not rigid anchoring to the ground.

## Constraints (must satisfy)
- **Contact**: The structure should only touch the pivot. Any contact with the ground (below the pivot level) will lead to failure.
- **Mass Budget**: No explicit limit, but structural efficiency is key to maintaining balance.
- **Beam Limits**: Individual beams must stay within width <= 7.0m and height <= 2.0m.
""",
    
    'success_criteria': """
## Success Criteria
1. **Load Attachment**: Successfully catch or connect to the heavy load at x=3.0.
2. **Static Balance**: Maintain the main beam's angle within ±10 degrees for at least 15 seconds after the load is supported.
3. **No Grounding**: The structure does not touch the ground or any surface other than the pivot.

## Design Constraints
- **Beam size**: 0.1 <= width <= 7.0 m, 0.1 <= height <= 2.0 m.
- **APIs**: Use only the primitives documented below.
""",
    
    'primitives_api': API_INTRO + ADD_BEAM + ADD_JOINT_RIGID + GET_STRUCTURE_MASS + ACCESS_TERRAIN_BODIES,
}
