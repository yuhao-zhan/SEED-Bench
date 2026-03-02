"""
D-02: The Jumper task Prompt (FUNDAMENTAL: pit has narrow slots—trajectory must pass through gaps only)
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM_01_4,
    ADD_JOINT_GROUND_ANCHOR,
    GET_JUMPER,
    GET_STRUCTURE_MASS,
    SET_JUMPER_VELOCITY,
    SET_MATERIAL_PROPERTIES_STATICS,
)

TASK_PROMPT = {
    "task_description": """
You need to design a mechanism that launches a jumper across a deep pit to land on the far platform.

## CRITICAL: Three narrow "gates" in the pit — trajectory must pass through the gaps only
- In the middle of the pit there are **three vertical slots (gates)**. Each slot is a **narrow vertical gap** between a **lower red bar** and an **upper red bar** (ceiling). The allowed path is only through these gaps — not above, not below.
- **Touching any red bar = fail**: If the jumper **touches** (any contact with) any red bar — either the lower or the upper bar of any slot — the task fails. You must pass **through** each gap without touching the bars above or below.
- You can **observe** in the simulation: three pairs of red horizontal bars in the pit; the gap between each pair is the only safe corridor. The gaps are **narrow** (on the order of about one meter in height). Exact positions and heights are **not** given — you must find a trajectory that threads through all three gaps by trial (e.g. by adjusting launch angle and speed).
- The jumper is a block (roughly 0.8 m × 0.6 m). It must pass through all three gaps and land on the far platform.

## Task Environment
- **Left platform**: Solid ground on the left (take-off side), top surface around y ≈ 1 m.
- **Pit**: A wide gap; in the middle, the three red-bar pairs form the narrow slots described above.
- **Right platform**: Solid ground on the right; the jumper must land here (top surface around y ≈ 1 m).
- **Build zone**: x=[1.5, 6.5] m, y=[2.5, 5.5] m. All beam centers must lie inside this zone.
- **Jumper**: Starts at rest in the build area (e.g. around the middle of the build zone). You launch it via agent_action using set_jumper_velocity so it **passes through all three gaps without touching any red bar** and lands on the right platform.
- **Gravity**: About 14 m/s² downward.

## Task Objective
Design a launcher that:
1. Produces a trajectory that **passes through all three narrow gaps** (between lower and upper red bars) without touching any red bar.
2. Lands the jumper on the right platform.
3. Stays within the build zone and material budget.
""",
    "success_criteria": """
## Success Criteria
1. **No touch on red bars**: The jumper must not touch any red bar (lower or upper) at any of the three slots.
2. **Landing**: Jumper reaches and stays on the right platform (center on the far side, on or above the platform surface).
3. **No fall**: Jumper must not fall into the pit (must not go below the pit floor before landing on the right side).

## Failure Conditions
- **Touched red bar**: Any contact with any red bar (above or below) = immediate fail.
- **Outside slot**: Passing above the ceiling or below the floor of a slot (touching the bars) = fail.
- **Fall into pit**: Jumper never reaches the right platform, or falls below the pit floor.

## Design Constraints
- **Build zone**: x=[1.5, 6.5], y=[2.5, 5.5]. All beam centers must lie inside.
- **Beam limits**: Each beam 0.1 <= width, height <= 4.0 m.
- **Anchors**: `add_joint(body, None, anchor_point, ...)` anchors to the left platform.
- **Material budget**: Total launcher mass (beams only) < 180 kg.
- **Launch**: Use `set_jumper_velocity(vx, vy)` in agent_action to launch (e.g. on first step).
""",
    "primitives_api": API_INTRO
    + ADD_BEAM_01_4
    + ADD_JOINT_GROUND_ANCHOR
    + GET_JUMPER
    + GET_STRUCTURE_MASS
    + SET_JUMPER_VELOCITY
    + SET_MATERIAL_PROPERTIES_STATICS,
}
