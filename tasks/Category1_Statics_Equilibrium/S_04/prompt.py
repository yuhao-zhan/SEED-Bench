"""
S-04: The Balancer task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM_01_10,
    ADD_JOINT_STATICS,
    GET_STRUCTURE_MASS,
)

ACCESS_TERRAIN_BODIES = """
### Access Terrain Bodies
```python
terrain_body = sandbox._terrain_bodies.get("key")
```
- Returns the static/dynamic terrain object for the given key, or None.
- **Available keys**: "pivot", "load"
"""

TASK_PROMPT = {
    'task_description': """
Build a structure on a sharp pivot (0,0) that balances an asymmetric load.
You must build a structure that keeps the system level.

## Task Environment
- **Pivot**: Sharp static triangle at (0,0), tip radius 0.05m.
- **The Load**: A 200kg block at (3, 0). It auto-attaches (welds) to the first structure body whose center is within 0.5m of (3,0). If no structure is near (3,0), the load falls and you fail.
- **Beam Limits**: Each beam: 0.1 <= width <= 7.0 m, 0.1 <= height <= 2.0 m (enforced at build time).

## Task Objective
Design a balanced structure that:
1. Has a part near (3,0) so the load attaches
2. Connects to the pivot at (0,0)
3. Maintains level orientation (±10 degrees) for 15 seconds. The structure must be free to rotate about the pivot (balance is evaluated with respect to rotation).
""",
    
    'success_criteria': """
## Success Criteria
1. **Catch**: Successfully connect to the load at (3,0) (load auto-attaches when structure is within 0.5m).
2. **Balance**: Keep the main beam (first created body) angle within ±10 degrees for 15s.

## Design Constraints
- **Contact**: Only touch the pivot. Touching ground (y < -0.1) is failure.
- **Beam size**: No beam may have width > 7.0 m or height > 2.0 m (enforced at build time).
""",
    
    'primitives_api': API_INTRO + ADD_BEAM_01_10 + ADD_JOINT_STATICS + GET_STRUCTURE_MASS + ACCESS_TERRAIN_BODIES,
}
