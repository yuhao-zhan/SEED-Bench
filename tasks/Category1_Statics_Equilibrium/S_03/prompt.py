"""
S-03: The Cantilever task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM_01_10,
    ADD_JOINT_STATICS,
    GET_STRUCTURE_MASS,
    GET_STRUCTURE_REACH,
)

ACCESS_TERRAIN_BODIES = """
### Access Terrain Bodies
```python
terrain_body = sandbox._terrain_bodies.get("key")
```
- Returns the static/dynamic terrain object for the given key, or None.
- **Available keys**: "wall"
"""

TASK_PROMPT = {
    'task_description': """
Construct a horizontal structure anchored ONLY to the left wall.
It must extend as far right as possible and support TWO loads: a tip load and a mid-span load.
Warning: You have only 2 wall anchors, and each breaks if torque exceeds 2600 Nm. You must design so that a node exists in x=[5, 10] for the mid-span load (closest to 7.5m is selected).

## Task Environment
- **Wall**: Vertical static wall at x=0. Maximum 2 anchor points.
- **Load 1 (tip)**: A 600kg weight attaches to your right-most node at t=5s.
- **Load 2 (mid-span)**: A 400kg weight attaches at t=10s to the node whose center is closest to x=7.5m among nodes with x in [5, 10]. You must design so that at least one node exists in this range.
- **Beam Limits**: Each beam: 0.1 <= width <= 10.0 m, 0.1 <= height <= 2.0 m (enforced at build time). The vertical extent of each beam is limited so the structure resembles a horizontal cantilever.

## Task Objective
Design a cantilever structure that:
1. Extends horizontally from the wall
2. Reaches at least x=14m
3. Supports 600kg at the tip (from t=5s) and 400kg at mid-span (from t=10s) for 10s each after attachment
4. Uses at most 2 wall anchors; distributes stress so no anchor exceeds 2600 Nm
5. **Stiffness**: The tip must NOT sag below y=-2.5m. Excessive droop fails the task.
""",
    
    'success_criteria': """
## Success Criteria
1. **Reach**: Tip x >= 14m.
2. **Load Bearing**: Hold tip load (600kg) for 10s after t=5s, and mid-span load (400kg) for 10s after t=10s.
3. **Anchor Integrity**: No wall anchors break (torque <= 2600 Nm per anchor).
4. **No Excessive Sag**: Tip must stay above y=-2.5m throughout. If the tip drops to or below -2.5m, the task fails.

## Design Constraints
- **Anchor Limits**: Maximum 2 anchor points on the wall.
- **Anchor Strength**: Each wall joint breaks if Torque > 2600 Nm. (Key Challenge!)
- **Geometry**: Must extend to at least x=14m and provide a node in x=[5, 10] for the second load (closest to 7.5m is selected).
- **Stiffness**: Design must limit deflection; tip below y=-2.5m fails the task.
- **Beam height**: No beam may have height > 2.0 m (enforced at build time).
""",
    
    'primitives_api': API_INTRO + ADD_BEAM_01_10 + ADD_JOINT_STATICS + GET_STRUCTURE_MASS + GET_STRUCTURE_REACH + ACCESS_TERRAIN_BODIES,
}
