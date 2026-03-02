"""
D-04: The Swing task Prompt and Primitives definition (HARD variant: apex in zone or vertical fall)
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM_01_3,
    ADD_JOINT_GROUND_ANCHOR,
    APPLY_FORCE_TO_SEAT,
    APPLY_IMPULSE_TO_SEAT,
    GET_SIM_TIME,
    GET_STRUCTURE_MASS,
    GET_SWING_SEAT,
    GET_WIND_FORCE_AT_TIME,
    SET_MATERIAL_PROPERTIES_STATICS,
)

TASK_PROMPT = {
    "task_description": """
You need to make the swing reach the **red target zone** in a controlled way: the seat must either (1) be **at rest at the highest point (apex)** inside the red zone, or (2) **fall vertically** (nearly straight down) into the red zone after an apex. Heavy seat, damping, **strong wind and gusts**, tight target, and **pump force limit**.

## Task Environment
- **Ground**: Flat surface, top at y=0.5 m.
- **Pivot**: The swing is attached to a fixed pivot at (10, 10) m. The rope length is 4 m, so the seat hangs at (10, 6) m at rest.
- **Seat**: Heavy (high density) with **linear and angular damping** — energy is lost every step.
- **Wind**: **Strong periodic wind** (amplitude ~12 N, period ~2.8 s) and **random gusts** act on the seat. Use get_wind_force_at_time and get_sim_time for wind-aware timing.
- **Target (red zone)**: y >= 11.7 m, x in [9.35, 10.65] m. Success requires **one** of:
  - **(1) Apex in zone**: The seat is inside the red zone **with speed < 1.0 m/s** (at the highest point, velocity ≈ 0).
  - **(2) Vertical fall into zone**: After the seat has reached an apex (speed < 1.0 m/s at some time), the seat is inside the red zone **falling vertically** (vy < 0 and |vx| < 1.35 m/s).
- **Pump force limit**: At most **42 N** horizontal per step (sandbox.MAX_PUMP_FORCE).
- **Build Zone**: x=[6, 14] m, y=[4, 10] m. **Material budget < 100 kg.**

## Task Objective
Design a mechanism that pumps the swing using phase-synchronized resonance and wind-aware timing (respect 42 N limit). Control energy so that the apex lies inside the red zone, OR so that the seat falls vertically into the red zone after an apex.
""",
    "success_criteria": """
## Success Criteria (one of the following)
1. **Apex in zone**: At some step, the swing seat is inside the red zone (y >= 11.7 m, x in [9.35, 10.65] m) and its **speed < 1.0 m/s** (at rest at the highest point).
2. **Vertical fall into zone**: At some step after the seat has reached an apex (speed < 1.0 m/s), the seat is inside the red zone with **vy < 0** (falling) and **|vx| < 1.35 m/s** (nearly vertical fall).

## Failure Condition
- **Did not succeed**: The seat never satisfies (1) or (2).

## Design Constraints
- **Build Zone**: x=[6, 14], y=[4, 10]. All beam centers must lie inside.
- **Beam limits**: Each beam 0.1 <= width, height <= 3.0 m.
- **Material Budget**: Total mechanism mass < 100 kg.
- **Pump force limit**: |fx| <= 42 N per step when calling apply_force_to_seat.
""",
    "primitives_api": API_INTRO
    + ADD_BEAM_01_3
    + ADD_JOINT_GROUND_ANCHOR
    + GET_SWING_SEAT
    + APPLY_FORCE_TO_SEAT
    + APPLY_IMPULSE_TO_SEAT
    + GET_WIND_FORCE_AT_TIME
    + GET_SIM_TIME
    + GET_STRUCTURE_MASS
    + SET_MATERIAL_PROPERTIES_STATICS,
}
