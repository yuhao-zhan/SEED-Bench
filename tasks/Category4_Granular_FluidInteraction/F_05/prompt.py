"""
F-05: The Boat task Prompt (EXTREME: 4 rocks, current, rogue double-hit, lateral gusts, 60 kg, 18°, y≥2.0)
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM_01_1,
    ADD_JOINT_GROUND_ANCHOR,
    GET_STRUCTURE_MASS,
    SET_MATERIAL_PROPERTIES_STATICS,
)

TASK_PROMPT = {
    "task_description": """
You need to design structure (e.g. rails, ties, ballast) on a boat so that cargo does not fall into the water in **extreme conditions**: multi-mode waves, gusts, **lateral wind**, **water current**, **rogue waves (often double-hit)**, **sudden lateral gusts** (periodic strong sideways impulses), and **four floating rocks** in the water that the boat collides with frequently.

## Task Environment (EXTREME)
- **Water**: Zone x=5m to x=25m, surface at y=2m. **Water current** pushes the boat away from center (x=15). **Multi-mode waves**, **gusts**, and **rogue waves** (large vertical impulses, sometimes a second hit a few steps later) excite the boat.
- **Floating obstacles**: **Four rocks** are placed along the boat path in the water. Collisions cause strong impulses; keep all cargo on board despite repeated impacts.
- **Wind**: **Lateral wind** (periodic) and **sudden lateral gusts** (periodic strong sideways force every ~200 steps) induce roll and knock cargo.
- **Boat**: Hull (3m x 0.4m) at x=15m, y≈2.5m. **Stability**: hull angle must not exceed **18°** from horizontal (strict capsize limit).
- **Cargo**: **10** round cargo (radius 0.15m, heavy and **very slippery**). Cargo below **y=1.98m** counts as "in water" (lost).
- **Build Zone**: x=[12, 18], y=[2, 4.5]. Anchor to the boat or floor.
- **Floor**: Continuous at y=0.
""",
    "success_criteria": """
## Success Criteria
1. **Cargo**: No cargo in water (all must remain above **y=1.98m**).
2. **Stability**: Boat must not capsize (hull angle must not exceed **18°** from horizontal).
3. **Integrity**: Your added structure remains intact (joints do not break).

## Design Constraints
- **Build Zone**: x=[12, 18], y=[2, 4.5]. All beams within this zone.
- **Beam limits**: 0.1 <= width, height <= 1.0 m.
- **Anchors**: Use `add_joint(body, None, anchor_point, ...)` to anchor to the floor or boat.
- **Material Budget**: Total added structure mass **< 60 kg**.
""",
    "primitives_api": API_INTRO
    + ADD_BEAM_01_1
    + ADD_JOINT_GROUND_ANCHOR
    + GET_STRUCTURE_MASS
    + SET_MATERIAL_PROPERTIES_STATICS,
}
