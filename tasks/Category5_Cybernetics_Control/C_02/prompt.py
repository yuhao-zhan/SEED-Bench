"""
C-02: The Lander task prompt (hard variant: obstacle + partial observability + moving platform)
"""
from ...primitives_api import (
    API_INTRO,
    GET_LANDER_BODY,
    GET_LANDER_POSITION,
    GET_LANDER_ANGLE,
    GET_LANDER_ANGULAR_VELOCITY,
    GET_GROUND_Y_TOP,
    GET_LANDER_SIZE,
    APPLY_THRUST,
    GET_REMAINING_FUEL,
)

TASK_PROMPT = {
    "task_description": """
You must control a lander craft by applying thrust so that it soft-lands on the ground in a valid area.

## Task Environment
- **Ground**: A horizontal surface. The lander starts above the ground; its starting position may not coincide with the valid landing area.
- **Lander**: Box craft (0.8 m × 0.6 m), mass 50 kg. Thrust is along the craft's own "up" direction (body frame). The craft is subject to environmental disturbances (wind, gusts) that you must counteract.
- **Gravity**: 10 m/s² downward.
- **Valid landing area**: The horizontal region where touchdown is accepted **depends on when you touch down**. The zone moves with time (moving platform); use step_count to relate to valid zone.
- **Forbidden zone (obstacle)**: Between the start and the landing area there is a **no-fly zone**. If the craft enters this zone **below a certain height**, the run fails immediately. You must **go around** the obstacle (climb above it, then cross to the landing side, then descend).
- **Thrust**: You command main thrust and steering torque. Main thrust consumes fuel (impulse); when fuel is exhausted, main thrust has no effect. Steering torque does not consume fuel.
- **Actuation**: Commands take effect after a delay (several steps); observe behavior to infer.
- **Success also requires landing with at least a minimum amount of fuel remaining** (fuel-efficient trajectory).

## Observability (critical)
- **Velocity (vx, vy) is not directly observable.** You have access only to position (x, y), angle, angular velocity, step count, and fuel. If your control law needs velocity (e.g. for soft landing), you must **infer it from position history** (e.g. (x - x_prev) / dt).

## Constraints
- **Soft landing**: Vertical impact speed at touchdown must not exceed 2.0 m/s.
- **Landing zone**: Touchdown must occur within the valid horizontal zone **at the time of touchdown**.
- **Attitude**: Land with tilt |angle| ≤ ~0.15 rad (roughly upright); capsizing fails.
- **Fuel**: Must land with at least ~350 N·s fuel remaining (total ~5500 N·s).
- **Obstacle**: No-fly zone boundaries (x, y) are discoverable via feedback; climb above before crossing right.

## Task Objective
Implement `agent_action(sandbox, agent_body, step_count)` so that the lander:
1. Never enters the forbidden zone below the safe height—climb first, then cross to the landing side, then descend.
2. Touches the ground with vertical impact speed ≤ 2.0 m/s (soft landing).
3. Touches down within the valid horizontal zone at that moment.
4. Lands roughly upright with sufficient fuel remaining.

You may ONLY use the APIs documented below. Do not access internal attributes.
""",
    "success_criteria": """
## Success Criteria
1. **Soft landing**: Vertical impact speed at touchdown ≤ 2.0 m/s.
2. **Landing zone**: Touchdown within the valid horizontal zone at the time of touchdown.
3. **Attitude**: Land with tilt within allowed range (roughly upright).
4. **Fuel**: Land with at least minimum fuel remaining.
""",
    "primitives_api": API_INTRO
    + """
## Required Code Structure

### 1. build_agent(sandbox)
Return the lander body (pre-built).
```python
def build_agent(sandbox):
    return sandbox.get_lander_body()
```

### 2. agent_action(sandbox, agent_body, step_count)
Called every step. Use get_lander_size() and get_ground_y_top() to compute height above ground. Estimate velocity from position history (no velocity API).
"""
    + GET_LANDER_BODY
    + GET_LANDER_POSITION
    + GET_LANDER_ANGLE
    + GET_LANDER_ANGULAR_VELOCITY
    + GET_GROUND_Y_TOP
    + GET_LANDER_SIZE
    + APPLY_THRUST
    + GET_REMAINING_FUEL,
}
