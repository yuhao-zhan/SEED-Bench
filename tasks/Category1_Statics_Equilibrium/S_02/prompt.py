"""
S-02: The Skyscraper task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM_01_10,
    ADD_JOINT_STATICS,
    ADD_SPRING,
    GET_STRUCTURE_MASS,
    GET_STRUCTURE_BOUNDS,
)

ACCESS_TERRAIN_BODIES = """
### Access Terrain Bodies
```python
terrain_body = sandbox._terrain_bodies.get("key")
```
- Returns the static/dynamic terrain object for the given key, or None.
- **Available keys**: "foundation"
"""

TASK_PROMPT = {
    'task_description': """
Build a tall tower on a narrow foundation that survives an earthquake.
You may consider passive damping to counteract vibrations.

## Task Environment
- **Foundation**: Static ground x=[-2, 2], y=0. Structure can only contact the ground within x=[-2, 2].
- **Earthquake**: Horizontal oscillation x(t) = 0.5 * sin(2.0 * t) starting at t=2s. The foundation itself moves.
- **Wind**: Constant lateral force of 100N applied to all structure blocks above y=20m.
- **Beam Limits**: Each beam: 0.1 <= width, height <= 10.0 m.

## Task Objective
Design a tall structure that can:
1. Reach a height greater than 30m
2. Survive earthquake vibrations
3. Resist wind forces
4. Maintain stability (center of mass within x=[-4, 4])
""",
    
    'success_criteria': """
## Success Criteria
1. **Height**: Initial height > 30m (topmost point).
2. **Survival**: Top point remains above y=25m after 30s of quake.
3. **Stability**: Center of mass must stay within x=[-4, 4].

## Design Constraints
- **Foundation Contact**: Structure can only touch ground within x=[-2, 2].
- **Target Height**: Topmost point must be > 30m.
- **Width Limit**: Structure width cannot exceed 8m.
""",
    
    'primitives_api': API_INTRO + ADD_BEAM_01_10 + ADD_JOINT_STATICS + ADD_SPRING + GET_STRUCTURE_MASS + GET_STRUCTURE_BOUNDS + ACCESS_TERRAIN_BODIES,
}
