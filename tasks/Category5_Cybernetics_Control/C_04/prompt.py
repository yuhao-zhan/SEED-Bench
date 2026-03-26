"""
C-04: The Escaper task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO
from tasks.Category5_Cybernetics_Control.C_04.environment import (
    ACTIVATION_X_MAX,
    ACTIVATION_X_MIN,
    AGENT_MASS,
    BACKWARD_FX_THRESHOLD,
    BACKWARD_SPEED_MAX,
    EXIT_X_MIN,
    EXIT_Y_MAX,
    EXIT_Y_MIN,
    FORCE_HISTORY_CAP,
    FPS,
    HOLD_STEPS,
    LOCK_GATE_FX,
    LOCK_GATE_X_MAX,
    LOCK_GATE_X_MIN,
    MAX_STEPS,
    ONEWAY_FORCE_RIGHT,
    ONEWAY_X,
    POS_ITERS,
    STATE_HISTORY_CAP,
    STRUCTURAL_IMPULSE_SCALE_K,
    VEL_ITERS,
    WHISKER_RANGE,
)

_structural_impulse_ns = STRUCTURAL_IMPULSE_SCALE_K * AGENT_MASS
_structural_impulse_ns_str = (
    f"{int(round(_structural_impulse_ns))}"
    if abs(_structural_impulse_ns - round(_structural_impulse_ns)) < 1e-6
    else f"{_structural_impulse_ns:.1f}"
)
_unlock_qual_fx_example = int(round(BACKWARD_FX_THRESHOLD - 1.0))

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'C_04' in _api_data and 'API_INTRO' in _api_data['C_04']:
    del _api_data['C_04']['API_INTRO']


TASK_PROMPT = {
    "task_description": f"""
Design a controller for a whisker-equipped robot to unlock and escape a narrow maze.

## Task Environment
- **Agent**: Mass 5.0 kg, disk radius 0.2 m, initial position (2.0, 1.5) m.
- **Gravitational vertical acceleration (m/s²)**: Use **`world.gravity.y`** (m/s²) as the authoritative value for the current run. The source environment’s numeric gravity magnitude is **not stated in this document**—infer from motion or runtime inspection.
- **Agent dynamics**: Linear damping (`linearDamping`) applies to translation; the numeric value is **not stated in this document**—infer from coast-down or runtime inspection. **fixedRotation** is enabled (translation only).
- **Contact dynamics**: Wall–agent friction and restitution are set on **Box2D** fixtures; numeric coefficients are **not stated in this document**—infer from motion and impacts.
- **Simulation integrator**: Fixed timestep **1/{FPS}** s ({FPS} Hz), Box2D velocity iterations **{VEL_ITERS}**, position iterations **{POS_ITERS}** (matches the source environment configuration).
- **Internal delay buffers**: Command-force history retains at most **{FORCE_HISTORY_CAP}** recent simulation steps; true pose and whisker histories retain at most **{STATE_HISTORY_CAP}** recent steps for delay simulation.
- **Time-varying horizontal forcing (baseline source)**: In addition to other channels, the simulator may apply oscillatory or otherwise time-dependent horizontal forces (e.g. wind-like terms). **Exact amplitudes, frequencies, and phase rules are not stated in this document**—infer from motion and feedback.
- **Environmental horizontal forcing**: Besides your commanded forces, the world can apply additional horizontal forces (constant back-current, height-dependent shear, and time-varying terms when active). **Except for the one-way assist parameters stated in their own bullet below**, remaining environmental horizontal effects are only partly enumerated—infer their net effect from motion and feedback.
- **Height-dependent horizontal shear (if active)**: Uses vertical position relative to an internal reference height; neither that reference nor the shear gradient magnitude is numerically stated here—infer from motion and feedback.
- **Whiskers**: Three sensors (forward +x, up +y, down -y), each range {WHISKER_RANGE} m.
- **Whisker stream delay (simulation steps)**: 0.
- **Position report delay (simulation steps)**: 0. **Reported vs physical pose**: When delay is 0, reported position matches physical position for exit, unlock, lock gate, and one-way bias. Other environmental effects may use **reported** pose, **physical** linear velocity, or **physical** height for participation rules depending on the active simulator configuration; those rules are **not** fully enumerated here. When delay is N>0, x-band memberships that rely on **reported** pose lag physical state by N simulation steps.
- **Passage**: Maze bounds x in [0, 20] m, y in [0, 3] m.
- **Maze outer shell (indices 0–3; lower-left x, y, width, height in m)**: floor (0.0, 0.0, 20.0, 0.5); ceiling (0.0, 2.5, 20.0, 0.5); left wall (0.0, 0.0, 0.5, 3.0); right wall (20.0, 0.0, 0.5, 3.0).
- **Maze walls (indices 4-6; lower-left x, y, width, height in m)**: internal wall 1 (5.0, 0.0, 0.2, 1.0); internal wall 2 (9.0, 1.8, 0.2, 1.2); internal wall 3 (14.0, 1.8, 0.2, 1.2).
- **Whisker blind band along x (m)**: none (When active, suppression uses **physical** body x—whisker raycasts use true pose—not reported position.)
- **Control lag (simulation steps before commanded force takes effect)**: 0.
- **One-way rightward assist**: While **reported** x **>** **{ONEWAY_X:.1f}** m, an additional constant **+{ONEWAY_FORCE_RIGHT:.1f}** N horizontal force acts on the agent in +x (in addition to any other environmental horizontal forcing).
- **Structural k (failure if collision normal impulse exceeds k * agent mass {AGENT_MASS:g} kg)**: k={STRUCTURAL_IMPULSE_SCALE_K} (impulse threshold {_structural_impulse_ns_str} N·s). Here the failure condition is **normal impulse > (k × {AGENT_MASS:g}) N·s** (k acts as an impulse-per-mass scale in N·s per kg).
- **Goal**: Reach the exit zone at the end of the passage.
- **Unlock condition**: Exit is locked by a force field while **reported** x is in [{LOCK_GATE_X_MIN:.1f}, {LOCK_GATE_X_MAX:.1f}] m (an additional repelling horizontal force of **{abs(LOCK_GATE_FX):g}** N in −x applies on the body while locked and reported x remains in that band). To unlock: **reported** position x in [{ACTIVATION_X_MIN:.1f}, {ACTIVATION_X_MAX:.1f}] m with **commanded** horizontal Fx (after control lag) **strictly less than {BACKWARD_FX_THRESHOLD:.1f} N** (e.g. {_unlock_qual_fx_example} N qualifies; {BACKWARD_FX_THRESHOLD:.1f} N does not), and **true** linear speed from **physical** velocity **< {BACKWARD_SPEED_MAX:.1f} m/s**, for at least **{HOLD_STEPS}** consecutive steps.
- **Exit zone**: x >= {EXIT_X_MIN:.1f} m, y in [{EXIT_Y_MIN:.1f}, {EXIT_Y_MAX:.1f}] m; after **unlock**, hold there for at least **{HOLD_STEPS}** consecutive steps using **reported** position (before unlock, time in the exit zone does **not** count toward this hold). When position report delay is enabled, the same reported pose applies.
- **Time limit**: At most {MAX_STEPS:,} simulation steps.

## Task Objective
Design a control loop that:
1. Uses whisker readings to navigate the winding passage.
2. Performs the unlock behavior in the activation zone.
3. Reaches the exit zone **after unlocking** and holds for at least **{HOLD_STEPS}** consecutive steps (hold counts only after unlock).
""",
    "success_criteria": f"""
## Success Criteria
1. **Unlock & Reach**: Unlock and reach x >= {EXIT_X_MIN:.1f} m, y in [{EXIT_Y_MIN:.1f}, {EXIT_Y_MAX:.1f}] m.
2. **Hold**: After unlock, at least **{HOLD_STEPS}** consecutive steps in the exit zone using **reported** position; before unlock, exit-zone occupancy does **not** count toward this hold.
3. **Survival**: Stay below the structural impulse limit: **{_structural_impulse_ns_str} N·s** at baseline (k={STRUCTURAL_IMPULSE_SCALE_K}); failure if normal impulse exceeds **k × ({AGENT_MASS:g} kg)** in N·s.

## Design Constraints
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['C_04'].values()),
}
