"""
C-05: Tight Temporal Chain task prompt.
"""
from ...primitives_api import (
    API_INTRO,
    GET_AGENT_BODY,
    GET_AGENT_POSITION,
    GET_AGENT_VELOCITY,
    GET_TRIGGERED_SWITCHES,
    GET_NEXT_REQUIRED_SWITCH,
    GET_COOLDOWN_REMAINING,
    APPLY_AGENT_FORCE,
)

TASK_PROMPT = {
    "task_description": """
You must control an agent to trigger three switches (zones) in the correct order: A, then B, then C.

## Task Environment
- **Terrain**: Path with ground, ramps, and a barrier. Layout: flat [0,4] at y=2; ramp up to platform [5,6] at y=3.5; ramp down; flat [7,12] at y=2.
- **Barrier**: A barrier blocks passage at x≈4.5. It opens only **after a delay** (e.g. ~70 steps) **following** when zone A is triggered. You cannot reach B until the barrier opens.
- **Agent**: Circular, radius 0.2 m, mass 3 kg. Spawns near (0.5, 1.95) m. You apply force (force_x, force_y) each step.
- **Force limits**: |force_x|, |force_y| ≤ 50 N.
- **Zones**: A at (2, 2), B at (4.95, 3.2) elevated, C at (8, 2). Must trigger in order A → B → C.
- **Gravity**: ~10 m/s² downward.

## Constraints
- **Temporal chain**: Zone B may only accept if you were recently in A; zone C may only accept if you were recently in B. Wrong timing or dawdling can make later zones never accept.
- **Cooldown**: After triggering a zone, there is a cooldown (e.g. ~55 steps) before the next zone can accept. Use get_cooldown_remaining().
- **Stay-to-trigger**: You must stay in each zone for some consecutive steps (with speed cap) for it to count. Merely passing through may not trigger.
- **Zone C**: May require that your path included an elevated section (recent max y above a threshold)—discover via feedback.
- **Barrier**: Must wait for barrier to open after A before moving toward B.

## Task Objective
Implement agent_action so that the agent triggers A first, then B, then C. Success only when all three have been triggered in that order. Discover the exact procedure (timing, path, cooldown) through interaction and feedback.

You may ONLY use the APIs documented below. Do not access internal attributes.
""",
    "success_criteria": """
## Success Criteria
1. **Correct sequence**: Trigger the first zone (A), then the second (B), then the third (C), in that order.
2. **Failure**: Wrong order, or failing to satisfy hidden timing/path conditions, fails the run (score 0).
""",
    "primitives_api": API_INTRO
    + """
## Required Code Structure

### 1. build_agent(sandbox)
Return the agent body (pre-built).
```python
def build_agent(sandbox):
    return sandbox.get_agent_body()
```

### 2. agent_action(sandbox, agent_body, step_count)
Called every step. Use position, next required switch, velocity, and step_count. Use get_cooldown_remaining() to know when next zone can accept.
```python
def agent_action(sandbox, agent_body, step_count):
    x, y = sandbox.get_agent_position()
    next_switch = sandbox.get_next_required_switch()
    triggered = sandbox.get_triggered_switches()
    cooldown = sandbox.get_cooldown_remaining()
    vx, vy = sandbox.get_agent_velocity()
    sandbox.apply_agent_force(fx, fy)
```
"""
    + GET_AGENT_BODY
    + GET_AGENT_POSITION
    + GET_AGENT_VELOCITY
    + GET_TRIGGERED_SWITCHES
    + GET_NEXT_REQUIRED_SWITCH
    + GET_COOLDOWN_REMAINING
    + APPLY_AGENT_FORCE,
}
