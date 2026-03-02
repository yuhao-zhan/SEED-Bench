"""
D-05: The Hammer — LATE safe window: bar away only at a LATE step (~400+).
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM_01_4,
    ADD_JOINT_GROUND_ANCHOR,
    BODIES_LIST,
    GET_STRUCTURE_MASS,
    SET_MATERIAL_PROPERTIES_STATICS,
)

TASK_PROMPT = {
    "task_description": """
You need to break a hard shell by delivering a large impact. The difficulty is **timing** — the solution is **not** "swing once and hit":

## 1. LATE safe window — bar is away only at a late step
- **Inside the slot**, a bar **oscillates vertically**. The head can pass only when the bar is **away** (e.g. at bottom of its motion). This **safe window occurs only at a LATE simulation step** (hundreds of steps in). So you **cannot** succeed by swinging early — the bar will block you. You must **wait** (hammer idle for many steps), then **start the swing** so the head reaches the slot **exactly when** the bar is away at that late step.

## 2. Multi-phase control — often THREE phases
- **Phase 1**: Start the swing **late** (at the right step) so the head reaches the slot when the bar is away.
- **Phase 2**: **Reduce** angular velocity so the head passes through the slot **slowly** during the window.
- **Phase 3**: After passing the slot, **re-accelerate** so the head has enough kinetic energy to **break the shell**.

## 3. Slot, pendulum, shell
- **Slot**: Narrow vertical gap at x ≈ 15; oscillating bar inside; touching walls or bar fails.
- **Pendulum**: Swinging rod; do not touch it.
- **Shell**: Behind the slot at (16, 2.6); breaks only if impact force > threshold.

## Task Objective
Design a **swinging hammer** (pivot + arm + heavy head) that:
1. **Late timing**: Pass through the slot **when the bar is away at the late window** — not "one quick swing".
2. **Multi-phase (often three)**: Set `arm.angularVelocity` at **at least two**, and often **three**, steps in agent_action — start late, slow through slot, re-accelerate for impact.
3. No pendulum / slot / bar contact; break the shell; stay in build zone and mass < 70 kg.
""",
    "success_criteria": """
## Success Criteria
1. **Break shell**: The shell is broken (impact force exceeds the threshold).
2. **No slot barrier contact**: The hammer did **not** hit the slot barrier (wall above or below the gap) or the **oscillating bar** before hitting the shell.
3. **No pendulum contact**: The hammer did **not** hit the pendulum before hitting the shell.
4. **No constraint violation**: All beam centers in build zone; total mass < 70 kg.

## Failure Conditions
- **Hammer hit slot barrier or oscillating bar**: If the hammer touches the barrier or the **oscillating bar** before breaking the shell, the task fails — you must pass **through** the gap when the bar is away.
- **Hammer hit pendulum**: If the hammer touches the pendulum before breaking the shell, the task fails.
- **Shell not broken**: Wrong trajectory (missed slot or shell), or impact too weak.

## Design Constraints
- **Build Zone**: x=[2, 12], y=[2, 8]. All beam centers must lie inside.
- **Beam limits**: Each beam 0.1 <= width, height <= 4.0 m.
- **Material Budget**: Total mass (beams only) < 70 kg.
- **Anchors**: Use `add_joint(body, None, anchor_point, ...)` to anchor to the ground.
- **Control**: In agent_action, use `arm = sandbox.bodies[0]` (first beam = arm) and set `arm.angularVelocity = value` (rad/s) at the appropriate steps. You may call it at multiple steps (often three): late start, slow through slot, re-accelerate for impact.
""",
    "primitives_api": API_INTRO
    + ADD_BEAM_01_4
    + ADD_JOINT_GROUND_ANCHOR
    + GET_STRUCTURE_MASS
    + SET_MATERIAL_PROPERTIES_STATICS
    + BODIES_LIST,
}
