"""
S-02: The Skyscraper task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM,
    ADD_JOINT_RIGID,
    ADD_SPRING_STATICS,
    GET_STRUCTURE_BOUNDS,
    ACCESS_TERRAIN_BODIES,
)

TASK_PROMPT = {
    'task_description': """
Build a tall tower on a narrow foundation that must survive an earthquake and strong wind.
You may consider structural damping to counteract vibrations.

## Task Environment
- **Foundation**: A static ground area at x=[-2, 2], y=0. Your structure can only contact the ground within this narrow zone.
- **Earthquake**: After an initial period, the foundation will undergo horizontal oscillations (earthquake). The foundation itself moves, and your structure must survive the vibrations.
- **Wind**: A constant lateral force is applied to all structural components above y=20m, simulating high-altitude wind.
- **Beam Dimensions**: 0.1 <= width, height <= 10.0 meters.

## Task Objective
Design a stable skyscraper structure that can:
1. Reach an initial height greater than 30m.
2. Maintain its integrity and height during and after the earthquake.
3. Resist lateral wind forces at high altitudes.
4. Maintain global stability (the structure's center of mass must remain within a safe lateral range).
""",
    
    'success_criteria': """
## Success Criteria
1. **Height**: Topmost point > 30m at start.
2. **Survival**: Structure remains standing (top point remains high) after the earthquake and wind duration.
3. **Stability**: Global center of mass stays within x=[-8, 8] relative to foundation.

## Design Constraints
- **Foundation Contact**: All ground contact must be within x=[-2, 2].
- **Height Requirement**: Must exceed 30m.
- **Width Limit**: Total structure width cannot exceed 12m.
- **APIs**: Use only the primitives documented below.
""",
    
    'primitives_api': API_INTRO + ADD_BEAM + ADD_JOINT_RIGID + ADD_SPRING_STATICS + GET_STRUCTURE_BOUNDS + ACCESS_TERRAIN_BODIES,
}
