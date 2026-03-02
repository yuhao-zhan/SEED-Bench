"""
D-06: The Catch — ESSENTIAL difficulty
Deflector cooperation, ball-ball coupling, sequential order.
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM_01_3,
    ADD_JOINT_GROUND_ANCHOR,
    BODIES_LIST,
    GET_STRUCTURE_MASS,
    SET_MATERIAL_PROPERTIES_STATICS,
)

TASK_PROMPT = {
    "task_description": """
You need to design a **catcher** for **SEVEN** heavy balls. Three mechanisms require **discovery through simulation**:

## 1. Deflector cooperation
A moving deflector bar in the central region redirects balls. **Do not try to block or avoid it.** Instead, **place your catcher where the deflector sends balls**. The deflector sends balls to **three focal regions** (left, middle-right, far-right). Their exact positions are NOT given — you must run the simulation and observe where deflected balls land, then position your catcher there.

## 2. Ball-ball collisions
Balls collide with each other. If two balls are in the catch zone at the same time before both are absorbed, their collision can eject one. Design for **sequential absorption** — each ball should be caught before the next arrives.

## 3. Sequential order
Balls must be caught in order. If ball N arrives at the catch zone before ball M (M<N) is fully caught, the task fails. Use low restitution to absorb quickly.

## Environment
- **Build zone**: x=[7, 11], y=[0.5, 5.5]. All beam centers must lie inside.
- **Forbidden zones** (no beam center x in these ranges): [8.5, 9.5], [7.35, 7.75], [7.78, 8.55], [10.0, 10.5], [7.18, 7.34].
- **Sweeper bands** (no beam center y in these ranges): [1.0, 1.5], [2.0, 2.5], [2.95, 3.55], [4.15, 4.75].
- **Pit failure**: Ball at y<0.72 with speed>1.0 m/s before caught = fail.
- **Joint limit**: ~880 N peak; sustained >760 N for 2 steps causes joint break.
- **Balls launch** at t=0, 0.4, 1.0, 1.3, 1.8, 2.2, 2.7 s.

## Task objective
Catch all seven balls (speed < 0.35 m/s in target x=[7,11], y=[0.5,5.5]). Cooperate with the deflector; absorb sequentially to avoid ball-ball pile-up.
""",
    "success_criteria": """
## Success Criteria
- All seven balls caught (speed < 0.35 m/s in target).
- No pit failure, no structure smashed (joint break).
- No sequential violation (each ball caught before the next arrives).
- No beam in sweeper bands or forbidden zones; beam count <= 9, mass < 10 kg.

## Design Constraints
- **Build zone**: x=[7, 11], y=[0.5, 5.5].
- **Beam limits**: Each beam 0.1 <= width, height <= 3.0 m.
- **Beam count**: <= 9 beams.
- **Mass**: Total structure mass < 10 kg.
- **Anchors**: At least one beam must be anchored via `add_joint(body, None, anchor, 'rigid')` — unanchored designs fail.
- **Forbidden zones** (beam center x): [8.5, 9.5], [7.35, 7.75], [7.78, 8.55], [10.0, 10.5], [7.18, 7.34].
- **Sweeper bands** (beam center y): [1.0, 1.5], [2.0, 2.5], [2.95, 3.55], [4.15, 4.75].
""",
    "primitives_api": API_INTRO
    + ADD_BEAM_01_3
    + ADD_JOINT_GROUND_ANCHOR
    + GET_STRUCTURE_MASS
    + SET_MATERIAL_PROPERTIES_STATICS
    + BODIES_LIST,
}
