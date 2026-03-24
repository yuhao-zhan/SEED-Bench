"""
C-03: The Seeker (Very Hard) task Prompt and Primitives definition
"""

import os
import json
import sys
import importlib.util

# Single source of truth for numeric thresholds shared with environment.py / evaluator.py
_prompt_dir = os.path.dirname(os.path.abspath(__file__))
_spec_c03_env = importlib.util.spec_from_file_location(
    "c03_environment_prompt", os.path.join(_prompt_dir, "environment.py")
)
_c03_env = importlib.util.module_from_spec(_spec_c03_env)
_spec_c03_env.loader.exec_module(_c03_env)
_HREF = _c03_env.HEADING_REFERENCE_MIN_TARGET_SPEED
_ACT_X0 = _c03_env.ACTIVATION_ZONE_X_MIN
_ACT_X1 = _c03_env.ACTIVATION_ZONE_X_MAX
_ACT_STEPS = _c03_env.ACTIVATION_REQUIRED_STEPS
_RDIST = _c03_env.RENDEZVOUS_DISTANCE_DEFAULT
_RZX0 = _c03_env.RENDEZVOUS_ZONE_X_MIN
_RZX1 = _c03_env.RENDEZVOUS_ZONE_X_MAX
_ICE_MU = _c03_env.ICE_PATCH_FRICTION_DEFAULT
_WIND_X0, _WIND_X1 = _c03_env.WIND_ZONE_X
_TVIS = _c03_env.TARGET_SENSOR_VISUAL_RADIUS
_IMPULSE = _c03_env.IMPULSE_BUDGET
_REL_SPD = _c03_env.RENDEZVOUS_REL_SPEED_DEFAULT
_TRACK = _c03_env.TRACK_DISTANCE_DEFAULT
_HEAD_TOL_DEG = _c03_env.RENDEZVOUS_HEADING_TOLERANCE_DEG_DEFAULT
_BZ0 = _c03_env.BLIND_ZONE_X_MIN
_BZ1 = _c03_env.BLIND_ZONE_X_MAX
_SPD_BLIND = _c03_env.SPEED_BLIND_THRESHOLD
_GY_TOP = _c03_env.DEFAULT_GROUND_Y_TOP
_TGT_Y_MIN = _GY_TOP + 0.5
_TGT_Y_MAX = _GY_TOP + 2.0

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'C_03' in _api_data and 'API_INTRO' in _api_data['C_03']:
    del _api_data['C_03']['API_INTRO']


TASK_PROMPT = {
    "task_description": f"""
Design a controller for a seeker craft to achieve multiple heading-aligned rendezvous with a dynamic target.

## Task Environment
- **Simulation clock**: Fixed timestep **1/60 s** per step (60 Hz). Step index *k* corresponds to time *k*/60 s (e.g. ~1.2 s ≈ 72 steps; slot widths are in steps). Each step uses Box2D with **10** velocity iterations and **10** position iterations per sub-step.
- **Effective acceleration field**: Infer from observed motion; no numeric acceleration vector is disclosed here.
- **Seeker**: Mass 20 kg, radius 0.35 m. Circle–ground contact **restitution 0.1**. A SINGLE thrust vector; magnitude capped at 200 N per command, applied only along current heading. Thrust commanded at step t is applied at step t+1 (one-step actuation delay). Heading turns toward the commanded direction at up to 0.12 rad/step (~7°/step). Default **linear damping 0.5** and **angular damping 0.5** on the seeker body (Box2D). Follow the numerics printed for your specific run. After any step where applied thrust exceeds 120 N, max commanded thrust is reduced to 40 N for the next 80 steps (cooldown).
- **Sensing**: `get_target_position()` returns a new delayed sample only every **5** simulation steps; otherwise it repeats the last reading. Effective delay is 2–6 steps (re-sampled every 120 steps); until the first resample, delay uses 4 steps. If seeker x is in [{_BZ0:.1f}, {_BZ1:.1f}] m (blind band) OR seeker speed exceeds {_SPD_BLIND:.1f} m/s, the reading does not update (stale). Infer target velocity from position history.
- **Scoring vs. sensing**: Rendezvous and tracking are graded on **true** target position and velocity (distance to target, relative speed, heading reference). The delayed sensor may disagree with what the evaluator uses. The target has **no** physical collision radius in simulation; any rendered disk (e.g. radius {_TVIS:g} m in the reference viewer) is **schematic only** and does not affect capture distance or overlap checks.
- **Activation Gate**: Rendezvous only counts after the seeker "activates" by staying in x in [{_ACT_X0:.1f}, {_ACT_X1:.1f}] m for at least {_ACT_STEPS} consecutive steps.
- **Moving Corridor**: Allowed seeker x is between x_lo and x_hi at each time t (seconds): x_lo = 8 + 2·sin(0.4·t), x_hi = 22 − 2·sin(0.4·t) (envelope roughly 6–24 m). **Pinch**: when sin(0.35·t − 32) > 0.25, both boundaries move inward by 2.0 m each (narrower passage). Violation if seeker center x leaves [x_lo, x_hi] by more than 0.02 m.
- **Spawn**: The seeker spawns at (11.0, 1.35) m (x, y).
- **Ground**: Ground segment length 30 m (world x ≈ 0–30 m); the ground body is a horizontal box with **half-height 0.5 m** (top surface at y = {_GY_TOP:.1f} m by default; `terrain_config["ground_y_top"]` overrides). **Restitution 0** on the ground (seeker–ground contact restitution remains **0.1** on the seeker fixture). Ground friction coefficient (seeker vs. ground contact) is 0.4.
- **Ice patches**: Two low-friction patches centered at (9.0, 1.25) and (16.5, 1.25) m, half-size 1.0×0.12 m, with **friction coefficient {_ICE_MU}** and **restitution 0** on the patch fixtures (seeker–patch contact).
- **Contact friction (Box2D)**: Each fixture carries its own friction coefficient; the engine combines contacting pairs, so effective slip on ice or obstacles is not determined by the seeker or the surface value alone—expect interaction where both coefficients matter.
- **Wind & Obstacles**: While seeker x ∈ [{_WIND_X0:.1f}, {_WIND_X1:.1f}] m, additional environmental forcing may act in the world frame. Curriculum runs may override default forcing through `terrain_config` without listing parameter names here; numeric values are not disclosed—infer effect from motion. There is **no** documented API primitive that reports instantaneous numeric components—infer from motion, drift, and evaluation feedback. **Moving obstacles** (kinematic boxes): (A) horizontal oscillation about x=10.5 m, amplitude 0.7 m, period 2.5 s, axis-aligned half-extents 0.35×0.55 m; (B) about x=17.0 m, amplitude 0.5 m, period 3.5 s, phase offset +0.8 s, half-extents 0.3×0.5 m. Moving boxes use surface **friction 0.5** and **restitution 0.1** (same as static boxes). **Static boxes**: centers (7.5, 1.5), (14.0, 1.5), (20.5, 1.5) m, half-extents 0.3×0.5 m, fixture friction 0.5, restitution 0.1. **Obstacle collision failure**: The run fails if the seeker penetrates **any** corridor box—**static or moving kinematic**—by at least ~0.05 m (deeper overlap than grazing; same threshold for all such boxes).
- **Target motion**: The target starts at **(12.0, 2.0) m** (defaults). Nominal direction changes every ~1.2 s. Random heading changes, jumps, and evasive boosts are driven by RNGs keyed off `terrain_config["target_rng_seed"]` when that key is set (curriculum/evaluation runs often supply a fixed seed, e.g. **123**, for reproducibility); when it is **unset**, built-in defaults use the same fixed seed (**42**) for target motion and sensor-delay resampling so trajectories stay reproducible for a fixed configuration. When the seeker is within about 4 m of the target **and** center-to-center separation is strictly greater than **0.01** m, the target’s velocity gains an extra component each step of **0.45·Δt** m/s along the unit vector **away** from the seeker (Δt = 1/60 s per step, i.e. **0.45 m/s²** effective escape acceleration); target speed magnitude is capped at **2.8 m/s** during that regime. Position clamped to x ∈ [6, 26] m and y ∈ [{_TGT_Y_MIN:.1f}, {_TGT_Y_MAX:.1f}] m (i.e. ground top y + 0.5 m through ground top y + 2.0 m; default ground top y = {_GY_TOP:.1f} m).
- **Fuel**: Total thrust impulse is limited to {_IMPULSE:.0f} N·s; **reaching or exceeding** that budget fails the run.
- **Horizon**: Slot step indices assume a long run (default max_steps = 10000 unless overridden). For a well-posed episode, **`max_steps` must be strictly greater than the upper bound of every phase-2 slot** returned by `sandbox.get_rendezvous_slots()` (default layout: the latest such bound is step **7300**).
- **Curriculum note**: Labeled numerics above describe the **Initial** environment. Mutated runs may replace specific values inline (including “originally … in the source environment”); always use `sandbox.get_rendezvous_slots()` for counting intervals on the current run. Other `terrain_config` fields (e.g. seeker mass/radius, spawn pose, target start, slot lists, impulse budget, thrust limits, obstacles, ice zones) and additional global or body parameters supplied by the runner may also override defaults—rely on the printed values for your run plus sandbox APIs.

## Task Objective
Design a multi-phase control strategy:
1. **Activation**: Position and hold the seeker in the activation zone until activated.
2. **Slotted Rendezvous**: Achieve two separate rendezvous in **designated** time slots (coarse windows [3700, 4800] and [6200, 7300] steps). Use `sandbox.get_rendezvous_slots()` for the exact `(lo, hi)` step intervals that count for this run (including any curriculum changes). You must complete the first in a phase-1 slot before the end of the phase-1 window, and the second in a phase-2 slot before the end of the phase-2 window; missing either window fails the run. Rendezvous counts only when the step is inside: phase 1 [3700,3800], [4200,4300], [4700,4800]; phase 2 [6200,6300], [6700,6800], [7200,7300]. Rendezvous only counts with seeker x in [{_RZX0:.1f}, {_RZX1:.1f}] m. Target nominal speed up to 1.5 m/s. Every 300 steps the target jumps by random dx, dy in [-1.2, 1.2] m.
   - Rendezvous requires: distance to target ≤ {_RDIST:.1f} m, matching velocity (relative speed < {_REL_SPD:g} m/s), AND seeker heading within {_HEAD_TOL_DEG:g}° of the reference direction: target **velocity** direction when target speed ≥ {_HREF:g} m/s, otherwise seeker-to-target direction.
3. **Tracking**: Maintain distance <= {_TRACK:g} m from the target after the second rendezvous.
""",
    "success_criteria": f"""
## Success Criteria
1. **Rendezvous Completion**: Successfully achieve rendezvous in both phase-1 and phase-2 **designated** time slots (coarse windows [3700, 4800] and [6200, 7300] steps) with correct heading alignment. Use `sandbox.get_rendezvous_slots()` for valid step intervals; phase-1 and phase-2 **windows** end at the max step index of their respective slot lists.
2. **Rendezvous capture envelope** (evaluator, when inside a counting slot): activation already achieved (≥{_ACT_STEPS} consecutive steps with seeker x ∈ [{_ACT_X0:.1f}, {_ACT_X1:.1f}] m); seeker x ∈ [{_RZX0:.1f}, {_RZX1:.1f}] m; distance to **true** target ≤ {_RDIST:.1f} m; relative speed < {_REL_SPD:g} m/s; heading within {_HEAD_TOL_DEG:g}° of target **velocity** direction if target speed ≥ {_HREF:g} m/s, else seeker-to-target direction.
3. **Tracking**: Maintain distance <= {_TRACK:g} m from target after the second rendezvous until the end.
4. **Safety**: No collisions with obstacles; stay within the moving corridor.
5. **Efficiency**: Total thrust impulse must not exceed **{_IMPULSE:.0f} N·s**; reaching or exceeding the budget fails the run.
6. **Episode completion**: A **success** score is awarded only on the **final** simulation step (when the run reaches `max_steps`, default 10000): you must still satisfy tracking, safety, and fuel at that instant after both rendezvous—not merely achieve two rendezvous earlier. **`max_steps` must be strictly greater than the maximum high end among phase-2 slots** from `sandbox.get_rendezvous_slots()` (defaults: last such index **7300**).
7. **Failure reporting precedence**: If more than one failure condition is true at the same time, the evaluator reports a single reason in this fixed order: thrust impulse budget reached or exceeded → left the allowed moving corridor → obstacle collision (penetration at or beyond the stated threshold) → missed phase-1 or phase-2 rendezvous window → distance to target exceeds the post-rendezvous track limit after both rendezvous are complete.

## Design Constraints
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['C_03'].values()),
}
