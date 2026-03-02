"""
F-02: The Amphibian task Prompt and Primitives definition (hard variant)
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM_15_2,
    ADD_JOINT_GROUND_ANCHOR,
    APPLY_FORCE_AMPHIBIAN,
    BODIES_LIST,
    GET_STRUCTURE_MASS,
    GET_VEHICLE_FRONT_X,
    SET_MATERIAL_PROPERTIES_STATICS,
)

TASK_PROMPT = {
    "task_description": """
You need to design an amphibian vehicle that can travel on land and cross a **hostile** body of water to reach the opposite shore.

## Task Environment
- **Left Bank**: Land from x=0 to x=10m. Build zone x=[2, 8], y=[0, 4].
- **Water**: x=10m to x=24m, depth 2m (surface y=2m). Buoyancy, **strong opposing current**, **quadratic drag**, **mid-water wind zone** (x≈12–22m), **deep channel** (x≈16.5–19.5m) with reduced buoyancy.
- **Three circular pillars** (obstacles) at x≈14, 17, 20. **Headwind burst** zone (x≈15–19m) adds extra opposing force.
- **Right Bank**: Land from x=24m. Reach at least x=26m to succeed.
- **Floor**: Continuous at y=0.

## Obstacles
- **Pillars**: Three circular obstacles; steer around or **rise over** (apply positive fy when front_x in pillar zones x≈11.5–16, 16–22).
- **Propulsion cooldown**: Each body can thrust only **every 3 steps**. Use **9 bodies** so 3 thrust each step.
- **Thrust limit**: ~520 N per body per step.
- **Mass budget**: < 600 kg.
""",
    "success_criteria": """
## Success Criteria
1. **Reach Shore**: Vehicle (rightmost part) reaches x ≥ 26m.
2. **No Sinking**: No part below y = -0.5.
3. **Integrity**: Structure remains intact.

## Design Constraints
- **Build Zone**: x=[2, 8], y=[0, 4]. All beams within this zone.
- **Beam limits**: 0.15 <= width, height <= 2.0 m.
- **Mass**: < 600 kg.
- **Anchors**: add_joint(body, None, ...) anchors to floor (vehicle must be able to move off).
- **Control**: Use apply_force(body, fx, fy, step_count=step_count) in agent_action. Use get_vehicle_front_x() for pillar/target detection.
""",
    "primitives_api": API_INTRO
    + ADD_BEAM_15_2
    + ADD_JOINT_GROUND_ANCHOR
    + GET_STRUCTURE_MASS
    + SET_MATERIAL_PROPERTIES_STATICS
    + APPLY_FORCE_AMPHIBIAN
    + GET_VEHICLE_FRONT_X
    + BODIES_LIST,
}
