"""
C-03: The Seeker task prompt (Hard: budget, corridor, rendezvous, time window, cooldown, evasive)
"""
from ...primitives_api import (
    API_INTRO,
    GET_SEEKER_BODY,
    GET_SEEKER_POSITION,
    GET_SEEKER_VELOCITY,
    GET_SEEKER_HEADING,
    GET_TARGET_POSITION,
    GET_REMAINING_IMPULSE_BUDGET,
    GET_CORRIDOR_BOUNDS,
    GET_TERRAIN_OBSTACLES,
    GET_LOCAL_WIND,
    APPLY_SEEKER_FORCE,
)

TASK_PROMPT = {
    "task_description": """
You must control a seeker vehicle to **rendezvous** with a moving target (get very close AND match its velocity) **in two separate time windows** during the run, then **track** it until the end.

## Task Environment
- **Ground**: Horizontal surface, length 30 m.
- **Seeker**: Circular vehicle, mass 20 kg, radius 0.35 m. Spawns at (11, 1.35) m.
- **Target**: Moving target; you have no direct velocity reading—estimate from position history.
- **Gravity**: 10 m/s² downward.

## Critical Constraints
1. **Thrust budget**: Total thrust impulse over the run is limited (~18500 N·s). Exceeding fails. Use get_remaining_impulse_budget() each step.
2. **Moving corridor**: You must stay inside a moving corridor at all times; the allowed x-interval changes over time and may narrow periodically. Use get_corridor_bounds() for current bounds. Leaving fails.
3. **Rendezvous**: You must achieve rendezvous (close + match velocity + **heading aligned with target velocity**) **twice**—in a first time slot and again in a later time slot. Rendezvous counts only in narrow time slots and only when seeker heading is aligned with target's velocity direction. Exact slots and region discover via feedback.
4. **Track**: After the second rendezvous, keep distance to target ≤ 7.5 m until the end (lose target = fail).

## Phenomena
- **Body-fixed thruster**: Thrust is applied only along the seeker's current heading. Heading turns toward commanded direction at limited rate (~7°/step).
- **Actuation delay**: Force commanded at step t is applied at step t+1.
- **Target position**: Updates only at certain intervals; may be unavailable in blind zone (x in [12, 15]) or when seeker speed exceeds threshold.
- **Thrust cooldown**: After heavy thrust, available thrust may be temporarily reduced for some steps.
- **Evasive target**: When distance < ~4 m, target may react; closing too aggressively can make rendezvous harder.
- **Activation gate**: Rendezvous may only count if seeker has first "activated" by staying in a zone for some consecutive steps—discover via feedback.

## Task Objective
Implement agent_action so that the seeker: stays in corridor, does not exceed budget, achieves first rendezvous (close + velocity matched + heading aligned) in one of the first-phase slots, then second rendezvous in a later slot, then tracks until end.

You may ONLY use the APIs documented below. Do not access internal attributes.
""",
    "success_criteria": """
## Success Criteria
- Stay within the moving corridor at all times.
- Do not exceed the thrust budget.
- Achieve first rendezvous (close + velocity matched + heading aligned) in one of the first-phase time slots.
- Achieve second rendezvous in one of the later time slots with same alignment.
- After the second rendezvous, track the target (distance ≤ 7.5 m) until the end.
""",
    "primitives_api": API_INTRO
    + """
## Required Code Structure

### 1. build_agent(sandbox)
Return the seeker body (pre-built).
```python
def build_agent(sandbox):
    return sandbox.get_seeker_body()
```

### 2. agent_action(sandbox, agent_body, step_count)
Called every step. Use step_count to plan timing. Maintain target position history to estimate target velocity (no velocity API). Check remaining impulse budget and corridor bounds every step.
"""
    + GET_SEEKER_BODY
    + GET_SEEKER_POSITION
    + GET_SEEKER_VELOCITY
    + GET_SEEKER_HEADING
    + GET_TARGET_POSITION
    + GET_REMAINING_IMPULSE_BUDGET
    + GET_CORRIDOR_BOUNDS
    + GET_TERRAIN_OBSTACLES
    + GET_LOCAL_WIND
    + APPLY_SEEKER_FORCE,
}
