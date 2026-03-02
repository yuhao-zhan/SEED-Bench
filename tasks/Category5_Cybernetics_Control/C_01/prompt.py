"""
C-01: Cart-Pole Swing-up then Balance task prompt.
Pole starts hanging down; agent must bring it to upright and keep it there.
"""
from ...primitives_api import (
    API_INTRO,
    GET_CART_BODY,
    GET_POLE_ANGLE,
    GET_POLE_ANGULAR_VELOCITY,
    GET_CART_POSITION,
    GET_CART_VELOCITY,
    APPLY_CART_FORCE,
)

TASK_PROMPT = {
    "task_description": """
You must control a cart on a horizontal track to bring a pole from its initial state to upright and then keep it balanced there.

## Task Environment
- **Track**: Horizontal, length 20 m. Cart is constrained to move only along the track (x-axis).
- **Cart**: Mass 10 kg. You apply horizontal force (positive = right, negative = left).
- **Pole**: Length 2 m, mass 1 kg, hinged at the top of the cart. Gravity pulls it down.
- **Gravity**: 10 m/s² downward.
- **Initial state**: The pole starts hanging downward (near the stable downward equilibrium) and at rest. It will not reach the upright position by itself; you must use the cart to bring it there and then hold it.

## Constraints and Limits
- **Safe zone**: Cart must stay within x in [1.5, 18.5] m at all times. Leaving this zone fails immediately.
- **Upright region**: Once the pole reaches |angle| ≤ 45° (upright band), it must stay there until the end. Leaving the upright region after having reached it causes failure.
- **Force limits**: Applied force is clamped to ±450 N.
- **Actuation**: Commands have rate limit (max change per step) and delay; response is not instantaneous.
- **Sensors**: Angle and angular velocity may have delay, noise, or bias; readings are not instantaneous.
- **Disturbances**: Random torque may act on the pole; base oscillation may affect the cart.

## Task Objective
Implement `agent_action(sandbox, agent_body, step_count)` to apply horizontal force so that:
1. The pole reaches the upright region (|angle| ≤ 45°) and remains there for the rest of the run.
2. The cart must remain within the safe zone [1.5, 18.5] m along the track.

You may ONLY use the APIs documented below. Do not access internal attributes.
""",
    "success_criteria": """
## Success Criteria
1. **Swing-up and hold**: The pole must reach the upright region (|angle| ≤ 45°) and stay there until the end of the run. Leaving the upright region after having reached it causes failure.
2. **Position**: The cart must stay within x in [1.5, 18.5] m at all times.
3. **Failure**: Run fails (score 0) if the cart leaves the safe zone, or if the pole leaves the upright region after having reached it.
""",
    "primitives_api": API_INTRO
    + """
## Required Code Structure

### 1. build_agent(sandbox)
Return the cart body (the controllable body).
```python
def build_agent(sandbox):
    return sandbox.get_cart_body()
```

### 2. agent_action(sandbox, agent_body, step_count)
Called every simulation step. Read state from sandbox and apply force to the cart.
```python
def agent_action(sandbox, agent_body, step_count):
    angle = sandbox.get_pole_angle()
    omega = sandbox.get_pole_angular_velocity()
    cart_x = sandbox.get_cart_position()
    cart_vx = sandbox.get_cart_velocity()
    # Your control: bring pole to upright, then keep it there
    sandbox.apply_cart_force(force)
```
You must first bring the pole from hanging down to upright, then keep it in the upright region.
"""
    + GET_CART_BODY
    + GET_POLE_ANGLE
    + GET_POLE_ANGULAR_VELOCITY
    + GET_CART_POSITION
    + GET_CART_VELOCITY
    + APPLY_CART_FORCE,
}
