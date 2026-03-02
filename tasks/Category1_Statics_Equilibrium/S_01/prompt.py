"""
S-01: The Bridge task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM_01_10,
    ADD_JOINT_STATICS,
    GET_STRUCTURE_MASS,
    SET_MATERIAL_PROPERTIES_STATICS,
)

ACCESS_TERRAIN_BODIES = """
### Access Terrain Bodies
```python
terrain_body = sandbox._terrain_bodies.get("key")
```
- Returns the static/dynamic terrain object for the given key, or None.
- **Available keys**: "left_cliff", "right_cliff", "vehicle_chassis", "vehicle_wheel1", "vehicle_wheel2", "water"
"""

TASK_PROMPT = {
    'task_description': """
You need to design a static bridge to connect two cliffs. A testing vehicle will cross it.

## Task Environment
- **Left Cliff**: Ends at x=10m, y=10m.
- **Right Cliff**: Starts at x=25m, y=10m.
- **Gap**: 15m wide between cliffs.
- **Vehicle**: Mass 2000kg, wheelbase 3m, spawns at x=5m on left cliff, moves right at 5 m/s.
- **Fail Zone**: Water at y=0m (vehicle falls in if it drops).
- **Deck Target**: The bridge deck must extend to at least x=30m for the vehicle to reach the target.

## Task Objective
Design a bridge structure that can:
1. Connect the two cliffs
2. Support the dynamic load of the vehicle (2000kg) moving at constant speed
3. Provide a continuous deck surface for wheels to roll over
4. Distribute load so joints do not break (joints have strength limits; excessive force/torque causes failure)
""",
    
    'success_criteria': """
## Success Criteria
1. **Passage**: Vehicle reaches x=30m.
2. **Integrity**: No structural breaks (joints remain intact; overloaded joints break and fail the task).
3. **Smoothness**: Vehicle vertical acceleration must not exceed 2g (bumpy roads fail).

## Design Constraints
- **Build Zone**: x=[10, 25], y=[5, 15]. Structure may extend beyond for the deck to reach x=30.
- **Beam Limits**: Each beam: 0.1 <= width, height <= 10.0 m. A single beam cannot exceed 10m in either dimension.
- **Anchors**: You may anchor your structure to the cliff walls.
- **Material Budget**: Total mass < 2000kg.
- **Road Surface**: Deck beams need friction > 0.5 for wheel traction.
""",
    
    'primitives_api': API_INTRO + ADD_BEAM_01_10 + ADD_JOINT_STATICS + GET_STRUCTURE_MASS + SET_MATERIAL_PROPERTIES_STATICS + ACCESS_TERRAIN_BODIES,
}
