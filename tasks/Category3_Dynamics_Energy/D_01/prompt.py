"""
D-01: The Launcher task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM_01_5,
    ADD_JOINT_GROUND_ANCHOR,
    ADD_SPRING_LAUNCHER,
    GET_GROUND,
    GET_PROJECTILE,
    GET_STRUCTURE_MASS,
    SET_MATERIAL_PROPERTIES_STATICS,
)

TASK_PROMPT = {
    "task_description": """
You need to design a launcher that propels a projectile to hit a distant target.

## Task Environment
- **Ground**: Flat surface at y=0 to y=1 m.
- **Build Zone**: x=[5, 15] m, y=[1.5, 8] m. All beam centers and anchors must lie inside this zone.
- **Projectile**: A ball (radius 0.25 m) starts at rest at position (10, 3) m. Your launcher must accelerate it toward the target.
- **Target Zone**: A vertical band (red box): x from 40 m to 45 m, **and** y from **2 m to 5 m**. Success requires the projectile **center** to be inside this rectangle (both x and y) at some time—**not** just rolling on the ground (y < 2 m) through the x range.

## Task Objective
Design a launcher that:
1. Uses levers, whip-like motion, and/or spring energy storage to propel the projectile.
2. Launches the projectile so that it reaches and hits the target zone (projectile center inside the band).
3. Stays within the build zone and material budget.
""",
    "success_criteria": """
## Success Criteria
1. **Hit**: Projectile center must lie **inside** the red target zone: **both** x in [40, 45] m **and** y in **[2, 5]** m at some time. Rolling on the ground (y < 2 m) through the x range is **not** sufficient.
2. **No early failure**: Projectile must not be destroyed or leave the simulation bounds.

## Failure Conditions
- **Miss**: Projectile does not enter the full zone (e.g. overshoots in x, or passes through the x band at a height outside y ∈ [2, 5] m).
- **Insufficient distance**: Projectile never reaches the target x range.

## Design Constraints
- **Build Zone**: All beam centers must lie within x=[5, 15], y=[1.5, 8]. Anchors should be in or near this zone.
- **Beam Limits**: Each beam 0.1 <= width, height <= 5.0 m.
- **Spring Stiffness**: 10 <= stiffness <= 3000 N/m.
- **Anchors**: Use `add_joint(body, None, anchor_point, ...)` to anchor to the ground.
- **Material Budget**: Total launcher mass (beams only) < 500 kg.
""",
    "primitives_api": API_INTRO
    + ADD_BEAM_01_5
    + ADD_JOINT_GROUND_ANCHOR
    + ADD_SPRING_LAUNCHER
    + GET_GROUND
    + GET_PROJECTILE
    + GET_STRUCTURE_MASS
    + SET_MATERIAL_PROPERTIES_STATICS,
}
