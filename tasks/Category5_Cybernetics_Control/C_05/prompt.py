"""
C-05: The Logic Lock task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from common.simulator import TIME_STEP
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'C_05' in _api_data and 'API_INTRO' in _api_data['C_05']:
    del _api_data['C_05']['API_INTRO']

# Standard episode horizon (must match evaluation/utils.py TASK_MAX_STEPS category_5_05)
C05_MAX_EPISODE_STEPS = 35000

TASK_PROMPT = {
    "task_description": f"""
Design a controller for an agent to trigger a "Logic Lock" by activating switches in a strict temporal and spatial sequence.

## Task Environment
- **Terrain layout**: World x roughly 0–12 m. Flat ground at y = 2 m for x in [0, 4] and [7, 12]; ramp up from (4, 2) toward platform; platform segment with top near y = 3.5 m for x in [5, 6]; ramp down toward y = 2 by x ≈ 7. Zone B sits on the elevated approach; zones A and C on the lower ground.
- **Solid terrain profile**: Flat segments, the platform, and ramp bodies use a vertical half-thickness of 0.25 m about the nominal top contact line (internal collision geometry).
- **Terrain & contact friction (Box2D coefficients)**: Ground 0.5; ramps 0.12; platform 0.45; agent body 0.4; barrier 0.3.
- **Switches**: Three switches (A, B, C). Zone A: center (2.0, 2.0) m, half-width 0.5 m, half-height 0.5 m. Zone B: center (4.95, 3.2) m, half-width 0.7 m, half-height 0.4 m. Zone C: center (8.0, 2.0) m, half-width 0.5 m, half-height 0.5 m.
- **Sequence**: Switches must be triggered in the order A -> B -> C. **Wrong order is fatal**: if the **next** required switch is still A, entering B or C fails the run; if the next required is B (after A has triggered), entering C before B has triggered fails the run. (Re-entering an **already triggered** zone, e.g. standing in A again after A fired, does not by itself fail.) **Time limit**: Not completing A→B→C before the episode step budget (below) ends counts as failure.
- **Activation duration**: The agent must stay inside a zone for 25 consecutive steps (with speed and force constraints below) to trigger it.
- **Speed cap inside zones**: Maximum velocity allowed inside a trigger zone for progress to count is 0.5 m/s; exceeding this resets that zone's progress.
- **Cooldown between triggers**: After triggering a zone, the agent must wait 55 steps before the next zone will accept progress.
- **Barrier**: A narrow vertical gate (half-width ≈ 0.08 m) at x = 4.5 m, spanning y from 0 to 4 m, blocks passage until it opens according to **Barrier delay after A** below.
- **Barrier delay after A**: The gate opens 70 steps after zone A is triggered, not immediately.
- **Temporal window A to B**: Zone B only counts stay-steps if the agent was in zone A within the last 160 steps.
- **Temporal window B to C**: Zone C only counts stay-steps if the agent was in zone B within the last 400 steps.
- **C altitude requirement**: Zone C only counts stay-steps if the agent's maximum y over the last 150 steps is at least 2.9 m (approach from elevated path).
- **Force limit inside zone**: Applying **controller** force with magnitude above 60 (same units as per-step API force) while inside a zone resets that zone's progress. Diagonal inputs near the per-axis cap can exceed this limit.
- **Repulsion**: Repulsive forces near B and C are anchored at each zone **center** (not zone edges). The field extends to a radius of 1.5 m. The **peak repulsion scale** at each zone center is 22.0 (same force units as per-step API force); strength decreases linearly with distance to zero at the field edge—**this characterizes the radial component**. The **peak tangential (swirling) scale** at each zone center is 0 (same force units as per-step API force), with the same linear falloff to zero at the field edge. The agent must navigate these fields (B until A triggered, C until B triggered).
- **Agent**: Spawn at (0.5, 1.95) m; radius 0.2 m; mass 3.0 kg. Passive velocity decay between control inputs follows unstated internal parameters—infer from motion alongside the zone speed cap.
- **Agent max applied force**: The controller can apply at most 50.0 force units per axis per step.
- **Collision and unstated dynamics**: Contacts use zero restitution (no bounce). Friction coefficients for terrain, agent, and barrier are stated above; any other simulator-side influences on motion are not enumerated here and may require inference from observations.

## Episode limit
- **Maximum steps per episode**: {C05_MAX_EPISODE_STEPS} simulation steps. The task must be completed within this horizon.
- **Simulation timestep**: Each physics step advances time by {TIME_STEP} s (fixed dt; "steps" in dwell/windows are simulation steps).

## Task Objective
Design a control loop that:
1. Navigates to switch A to begin the sequence.
2. After A triggers, reach B while the **Temporal window A to B** rule still holds, and cross only after the barrier opens per **Barrier delay after A**.
3. Trigger C while respecting **Cooldown between triggers**, **Temporal window B to C**, **C altitude requirement**, **Speed cap inside zones**, and **Force limit inside zone**.
4. Stay within speed cap (0.5 m/s) and force limit 60 inside zones so dwell time counts toward triggers.
""",
    "success_criteria": f"""
## Success Criteria
1. **Sequence Completion**: Switches A, B, and C triggered in the correct order and within their respective temporal/spatial windows.
2. **Efficiency**: Full A→B→C sequence completed within {C05_MAX_EPISODE_STEPS} simulation steps (including clearing the timed barrier once it opens).

## Design Constraints
- **Activation duration**: 25 steps per zone (with speed <= 0.5 m/s and force <= 60 inside zone).
- **Cooldown**: 55 steps between triggers.
- **Barrier delay**: 70 steps after A before gate opens.
- **Temporal windows**: A to B within 160 steps; B to C within 400 steps.
- **C altitude**: Recent max y >= 2.9 m over last 150 steps.
- **Friction**: Ground 0.5; ramps 0.12; platform 0.45; agent 0.4; barrier 0.3 (Box2D coefficients).
- **Repulsion**: Peak scale (radial component) 22.0 at zone centers; peak tangential (swirling) scale 0 (same units); field radius 1.5 m (linear falloff).
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['C_05'].values()),
}
