"""
C-03: The Seeker (Very Hard) task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'C_03' in _api_data and 'API_INTRO' in _api_data['C_03']:
    del _api_data['C_03']['API_INTRO']


TASK_PROMPT = {
    "task_description": """
Design a controller for a seeker craft to achieve multiple heading-aligned rendezvous with a dynamic target.

## Task Environment
- **Simulation clock**: Fixed timestep **1/60 s** per step (60 Hz). Step index *k* corresponds to time *k*/60 s (e.g. ~1.2 s ≈ 72 steps; slot widths are in steps). Each step uses Box2D with **10** velocity iterations and **10** position iterations per sub-step.
- **Gravity**: Infer the effective gravitational field from motion and dynamics; the specific acceleration vector is not disclosed for this environment.
- **Seeker**: Mass 20 kg, radius 0.35 m. Circle–ground contact **restitution 0.1**. A SINGLE thrust vector; magnitude capped at 200 N per command, applied only along current heading. Thrust commanded at step t is applied at step t+1 (one-step actuation delay). Heading turns toward the commanded direction at up to 0.12 rad/step (~7°/step). Default **linear damping 0.5** and **angular damping 0.5** on the seeker body (Box2D); curriculum `physics_config` may override these coefficients. After any step where applied thrust exceeds 120 N, max commanded thrust is reduced to 40 N for the next 80 steps (cooldown).
- **Sensing**: `get_target_position()` returns a new delayed sample only every **5** simulation steps; otherwise it repeats the last reading. Effective delay is 2–6 steps (re-sampled every 120 steps); until the first resample, delay uses 4 steps. If seeker x is in [12.0, 15.0] m (blind band) OR seeker speed exceeds 2.0 m/s, the reading does not update (stale). Infer target velocity from position history.
- **Scoring vs. sensing**: Rendezvous and tracking are graded on **true** target position and velocity (distance to target, relative speed, heading reference). The delayed sensor may disagree with what the evaluator uses.
- **Activation Gate**: Rendezvous only counts after the seeker "activates" by staying in x in [13.0, 17.0] m for at least 80 consecutive steps.
- **Moving Corridor**: Allowed seeker x is between x_lo and x_hi at each time t (seconds): x_lo = 8 + 2·sin(0.4·t), x_hi = 22 − 2·sin(0.4·t) (envelope roughly 6–24 m). **Pinch**: when sin(0.35·t − 32) > 0.25, both boundaries move inward by 2.0 m each (narrower passage). Violation if seeker center x leaves [x_lo, x_hi] by more than 0.02 m.
- **Spawn**: The seeker spawns at (11.0, 1.35) m (x, y).
- **Ground**: Ground segment length 30 m (world x ≈ 0–30 m); the ground body is a horizontal box with **half-height 0.5 m** (top surface at y = 1.0 m). **Restitution 0** on the ground (seeker–ground contact restitution remains **0.1** on the seeker fixture). Ground friction coefficient (seeker vs. ground contact) is 0.4.
- **Ice patches**: Two low-friction patches centered at (9.0, 1.25) and (16.5, 1.25) m, half-size 1.0×0.12 m, with unstated friction coefficient.
- **Wind & Obstacles**: While seeker x ∈ [14.0, 17.0] m, additional horizontal environmental forcing may act in the world frame. There is **no** documented API primitive that reports its instantaneous numeric components—infer its effect from motion, drift, and evaluation feedback. **Moving obstacles** (kinematic boxes): (A) horizontal oscillation about x=10.5 m, amplitude 0.7 m, period 2.5 s, axis-aligned half-extents 0.35×0.55 m; (B) about x=17.0 m, amplitude 0.5 m, period 3.5 s, phase offset +0.8 s, half-extents 0.3×0.5 m. Moving boxes use surface **friction 0.5** and **restitution 0.1** (same as static boxes). **Static boxes**: centers (7.5, 1.5), (14.0, 1.5), (20.5, 1.5) m, half-extents 0.3×0.5 m, fixture friction 0.5, restitution 0.1. **Obstacle collision failure**: The run fails if the seeker penetrates **any** corridor box—**static or moving kinematic**—by at least ~0.05 m (deeper overlap than grazing; same threshold for all such boxes).
- **Target motion**: The target starts at **(12.0, 2.0) m** (defaults). Nominal direction changes every ~1.2 s. Random heading changes, jumps, and evasive boosts use a **deterministic** RNG when no custom seed is set (same default seed as other built-in randomness), so trajectories are reproducible for a fixed configuration. When the seeker is within about 4 m of the target **and** center-to-center separation is strictly greater than **0.01** m, the target’s velocity gains an extra component each step of **0.45·Δt** m/s along the unit vector **away** from the seeker (Δt = 1/60 s per step, i.e. **0.45 m/s²** effective escape acceleration); target speed magnitude is capped at **2.8 m/s** during that regime. Position clamped to x ∈ [6, 26] m and y ∈ [1.5, 3.0] m (for default ground top y=1.0).
- **Fuel**: Total thrust impulse is limited to 18500 N·s; **reaching or exceeding** that budget fails the run.
- **Horizon**: Slot step indices assume a long run (default max_steps = 10000 unless overridden).
- **Curriculum note**: Labeled numerics above describe the **Initial** environment. Mutated runs may replace specific values inline (including “originally … in the source environment”); always use `sandbox.get_rendezvous_slots()` for counting intervals on the current run.

## Task Objective
Design a multi-phase control strategy:
1. **Activation**: Position and hold the seeker in the activation zone until activated.
2. **Slotted Rendezvous**: Achieve two separate rendezvous in **designated** time slots (coarse windows [3700, 4800] and [6200, 7300] steps). Use `sandbox.get_rendezvous_slots()` for the exact `(lo, hi)` step intervals that count for this run (including any curriculum changes). You must complete the first in a phase-1 slot before the end of the phase-1 window, and the second in a phase-2 slot before the end of the phase-2 window; missing either window fails the run. Rendezvous counts only when the step is inside: phase 1 [3700,3800], [4200,4300], [4700,4800]; phase 2 [6200,6300], [6700,6800], [7200,7300]. Rendezvous only counts with seeker x in [10.0, 20.0] m. Target nominal speed up to 1.5 m/s. Every 300 steps the target jumps by random dx, dy in [-1.2, 1.2] m.
   - Rendezvous requires: distance to target ≤ 6.0 m, matching velocity (relative speed < 1.8 m/s), AND seeker heading within 55° of the reference direction: target **velocity** direction when target speed ≥ 0.15 m/s, otherwise seeker-to-target direction.
3. **Tracking**: Maintain distance <= 8.5 m from the target after the second rendezvous.
""",
    "success_criteria": """
## Success Criteria
1. **Rendezvous Completion**: Successfully achieve rendezvous in both phase-1 and phase-2 **designated** time slots (coarse windows [3700, 4800] and [6200, 7300] steps) with correct heading alignment. Use `sandbox.get_rendezvous_slots()` for valid step intervals; phase-1 and phase-2 **windows** end at the max step index of their respective slot lists.
2. **Rendezvous capture envelope** (evaluator, when inside a counting slot): activation already achieved (≥80 consecutive steps with seeker x ∈ [13.0, 17.0] m); seeker x ∈ [10.0, 20.0] m; distance to **true** target ≤ 6.0 m; relative speed < 1.8 m/s; heading within 55° of target **velocity** direction if target speed ≥ 0.15 m/s, else seeker-to-target direction.
3. **Tracking**: Maintain distance <= 8.5 m from target after the second rendezvous until the end.
4. **Safety**: No collisions with obstacles; stay within the moving corridor.
5. **Efficiency**: Total thrust impulse must not exceed **18500 N·s**; reaching or exceeding the budget fails the run.
6. **Episode completion**: A **success** score is awarded only on the **final** simulation step (when the run reaches `max_steps`, default 10000): you must still satisfy tracking, safety, and fuel at that instant after both rendezvous—not merely achieve two rendezvous earlier.

## Design Constraints
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['C_03'].values()),
}
