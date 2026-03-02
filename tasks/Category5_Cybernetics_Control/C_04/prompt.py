"""
C-04: The Escaper task prompt — maze with behavioral unlock condition.
"""
from ...primitives_api import (
    API_INTRO,
    GET_AGENT_BODY,
    GET_AGENT_POSITION,
    GET_AGENT_VELOCITY,
    GET_WHISKER_READINGS,
    APPLY_AGENT_FORCE,
)

TASK_PROMPT = {
    "task_description": """
You must control an agent with whisker (raycast) sensors to escape a maze.

## Task Environment
- **Maze**: Bounded corridor x in [0, 20], y in [0, 3]. The right wall has an exit.
- **Exit zone**: x ≥ 18 m and y in a narrow vertical band [1.25, 1.45] m. Success requires **staying in this band for 60 consecutive steps** (not just reaching it once).
- **Agent**: Circular, radius 0.25 m, mass 5 kg. Spawns at (2, 2) m. You apply force (force_x, force_y) each step.
- **Force limits**: |force_x|, |force_y| ≤ 80 N.
- **Whiskers**: Three raycast sensors—front (+x), left (+y), right (-y). Each returns distance to nearest wall in meters (max 3 m).
- **Gravity**: 10 m/s² downward.

## Critical: Velocity Not Available
- **Velocity (vx, vy) is NOT provided.** get_agent_velocity() returns (0, 0) always. You must **infer velocity from position history** (e.g. store last (x, y) and step_count; vx ≈ (x - x_prev) / dt).

## What You Must Discover
- Obstacle layout and which passages lead forward—infer from whiskers and position.
- Regions that resist progress or apply extra forces—use velocity (estimated) and position over time.
- **What is required before the exit can be reached**—if going toward the exit fails (e.g. pushed back), the condition may be **on your behavior** (e.g. how you move, or applying force in a certain way for some time), not only on reaching a place. Infer from repeated tries and feedback.
- Whether going forward past some point prevents going back—if you advance too far before satisfying a condition, you may be unable to return.

## Task Objective
Implement agent_action so that the agent **holds** in the exit zone (x ≥ 18, y in [1.25, 1.45]) for **60 consecutive steps** before the step limit. Merely reaching the exit is not enough.

You may ONLY use the APIs documented below. Do not access internal attributes.
""",
    "success_criteria": """
## Success Criteria
1. **Escape**: Agent must hold in the exit zone (x ≥ 18 m, y in [1.25, 1.45] m) for 60 consecutive steps.
2. **Failure**: Step limit reached without holding in the exit for 60 consecutive steps (score 0, timeout).
""",
    "primitives_api": API_INTRO
    + """
## Required Code Structure

### 1. build_agent(sandbox)
Return the agent body.
```python
def build_agent(sandbox):
    return sandbox.get_agent_body()
```

### 2. agent_action(sandbox, agent_body, step_count)
Called every step. Read position and whiskers; **estimate velocity from position history** (get_agent_velocity returns 0,0). Apply force.
```python
def agent_action(sandbox, agent_body, step_count):
    x, y = sandbox.get_agent_position()
    front, left, right = sandbox.get_whisker_readings()
    # Estimate vx, vy from (x,y) history and step_count
    sandbox.apply_agent_force(fx, fy)
```
"""
    + GET_AGENT_BODY
    + GET_AGENT_POSITION
    + GET_AGENT_VELOCITY
    + GET_WHISKER_READINGS
    + APPLY_AGENT_FORCE,
}
