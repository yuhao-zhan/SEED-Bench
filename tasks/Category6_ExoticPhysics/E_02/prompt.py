"""
E-02: Thick Air (Hard) — prompt.
"""
from ...primitives_api import (
    API_INTRO,
    GET_CRAFT_POSITION,
    GET_CRAFT_VELOCITY,
    GET_HEAT,
    GET_OVERHEAT_LIMIT,
    IS_OVERHEATED,
    APPLY_THRUST_CRAFT,
    GET_STEP_COUNT,
)

TASK_PROMPT = {
    "task_description": """
You must move a craft to a target zone in a thick, viscous fluid. Thrust is required to make progress;
cumulative thrust use causes heating — exceed the heat budget and you fail.

## Task Environment
- **Start**: Craft (rigid body) starts near (8, 2) m.
- **Target**: Craft center must enter the zone: x in [28, 32] m, y in [2, 5] m.
- **Path**: Between start and target there are physical obstacles (narrow gaps you must pass through) and regions where the environment behaves differently (e.g. strong momentum loss, slippery-like effects, or time-varying disturbances). Exact positions and behaviors discover via get_craft_position(), get_craft_velocity(), get_heat(), get_overheat_limit(), and evaluation feedback.
- **Failure**: (1) Time runs out without the craft ever entering the target zone. (2) Overheat — cumulative thrust usage exceeds the heat limit (use get_overheat_limit() to check).

## Constraints
- **Overheat limit**: Use get_overheat_limit() to read the limit; stay under it.
- **Heat**: Cumulative |thrust|×time adds to heat; use get_heat() each step.

You may ONLY use the APIs documented below. Do not access internal attributes.
""",
    "success_criteria": """
## Success
- Craft center enters the target zone (x in [28, 32], y in [2, 5]) at some time.
- Heat stays below the overheat limit (use get_overheat_limit() and get_heat()).

## Failure
- Time out without ever entering the target zone.
- Overheat (heat ≥ limit).
""",
    "primitives_api": API_INTRO
    + """
## Required Code Structure

### 1. build_agent(sandbox)
Return None (craft is pre-built).
### 2. agent_action(sandbox, agent_body, step_count)
Called every step. Read position, velocity, heat; apply thrust. Use get_step_count() for time-varying disturbance compensation.
"""
    + GET_CRAFT_POSITION
    + GET_CRAFT_VELOCITY
    + GET_HEAT
    + GET_OVERHEAT_LIMIT
    + IS_OVERHEATED
    + APPLY_THRUST_CRAFT
    + GET_STEP_COUNT,
}
