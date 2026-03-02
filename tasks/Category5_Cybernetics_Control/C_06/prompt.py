"""
C-06: The Governor task prompt.
"""
from ...primitives_api import (
    API_INTRO,
    GET_WHEEL_BODY,
    GET_WHEEL_ANGULAR_VELOCITY,
    GET_TARGET_SPEED,
    APPLY_MOTOR_TORQUE,
)

TASK_PROMPT = {
    "task_description": """
You must control a wheel (rotor) to maintain constant angular speed under resisting load (governor / cruise control).

## Task Environment
- **Wheel**: Rotates about a fixed anchor. Radius 0.5 m, mass 10 kg. A load opposes rotation; its magnitude may depend on speed, may change over time, and may have a periodic component (e.g. with rotation).
- **Target speed**: Obtained each step via get_target_speed(); the target may change over time—use it every step.
- **Control**: You apply motor torque (N·m) each step. Positive torque = accelerate counterclockwise.
- **Gravity**: 10 m/s² downward; the wheel axis is fixed.

## Constraints
- **Stall**: If wheel speed stays below ~0.3 rad/s for many consecutive steps, the run fails.
- **Torque limits**: At very low speed, maximum torque may be reduced (speed-dependent). Infer from feedback if small corrections seem to do nothing.
- **Deadzone**: Very small torque requests (|torque| below ~2 N·m) may not take effect.
- **Measurement delay**: The reported angular velocity may be delayed by several steps; response may appear sluggish.

## Task Objective
Implement agent_action so that the wheel speed stays near the target (from get_target_speed()) and does not stall. Success = simulation runs to the step limit without stall and with mean speed error below a threshold. Use feedback metrics to infer behavior and tune control.

You may ONLY use the APIs documented below. Do not access internal attributes.
""",
    "success_criteria": """
## Success Criteria
1. **Regulate speed**: Wheel speed should stay near the target (from get_target_speed()) over the run.
2. **No stall**: If wheel speed remains below a low threshold for many consecutive steps, the run fails (score 0).
3. **Regulation quality**: Mean speed error over the run must stay below a threshold (infer from feedback).
""",
    "primitives_api": API_INTRO
    + """
## Required Code Structure

### 1. build_agent(sandbox)
Return the wheel body (pre-built).
```python
def build_agent(sandbox):
    return sandbox.get_wheel_body()
```

### 2. agent_action(sandbox, agent_body, step_count)
Called every simulation step. Read speed and target; apply motor torque to regulate speed.
```python
def agent_action(sandbox, agent_body, step_count):
    omega = sandbox.get_wheel_angular_velocity()
    target = sandbox.get_target_speed()
    # Design torque from omega, target, and optionally step_count or internal state
    sandbox.apply_motor_torque(torque)
```
"""
    + GET_WHEEL_BODY
    + GET_WHEEL_ANGULAR_VELOCITY
    + GET_TARGET_SPEED
    + APPLY_MOTOR_TORQUE,
}
