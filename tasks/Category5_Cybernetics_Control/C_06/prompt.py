"""
C-06: The Governor task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'C_06' in _api_data and 'API_INTRO' in _api_data['C_06']:
    del _api_data['C_06']['API_INTRO']

from common.simulator import TIME_STEP
from tasks.Category5_Cybernetics_Control.C_06.environment import (
    DEFAULT_WHEEL_ANGULAR_DAMPING,
    DEFAULT_WHEEL_MASS_KG,
    DEFAULT_WHEEL_RADIUS_M,
    MAX_STEPS,
    MEAN_SPEED_ERROR_THRESHOLD,
    MEASURE_DELAY_STEPS,
    REGULATION_START_STEP,
    STALL_SPEED_THRESHOLD,
    STALL_STEPS_THRESHOLD,
    TARGET_SPEED_RAD_S,
    TORQUE_DEADZONE,
    TORQUE_LIMIT_AT_ZERO,
    TORQUE_LIMIT_OMEGA_CAP_RAD_S,
    TORQUE_LIMIT_SLOPE,
)

TASK_PROMPT = {
    "task_description": f"""
Design a controller (a "governor") to maintain a wheel's rotation at the commanded target speed despite varying external loads.

## Task Environment
- **Wheel**: Single circular body (mass {DEFAULT_WHEEL_MASS_KG:g} kg, radius {DEFAULT_WHEEL_RADIUS_M:g} m) rotating about a fixed vertical axis through its center (revolute joint to the environment). The wheel body is subject to angular damping ({DEFAULT_WHEEL_ANGULAR_DAMPING:g} simulator units; adds speed-proportional resistance). Additional resisting torques and dynamics may be present—infer behavior from data rather than assuming a simple first-order plant.
- **Motor**: Each step you request motor torque; delivered torque magnitude is **capped** each step. The torque limit varies with rotational speed: at rest, the limit is {TORQUE_LIMIT_AT_ZERO:g} N·m, increasing by {TORQUE_LIMIT_SLOPE:g} N·m per rad/s until {TORQUE_LIMIT_OMEGA_CAP_RAD_S:g} rad/s. Additionally, an actuator **deadzone** of {TORQUE_DEADZONE:g} N·m applies, where requested torques with small absolute magnitudes will not be applied.
- **Target Speed**: The commanded angular velocity **can change during the run**; call the API **each step** for the current setpoint. Only the **initial** segment speed is stated here: {TARGET_SPEED_RAD_S} rad/s—later setpoints must be read from the API.
- **Angular velocity readout**: Use the documented API each step as your feedback signal for control. Note that measurements are **delayed** by {MEASURE_DELAY_STEPS} steps relative to the true instantaneous state.
- **Time discretization**: Each simulation step is {TIME_STEP:.6f} s ({int(round(1.0 / TIME_STEP))} Hz physics).
- **Opposing dynamics**: Resisting torques and disturbances are **not** fully specified here; they may vary with speed (including stiction effects at very low speeds), time, and internal state. Use closed-loop control and feedback to maintain tracking.

Design a control loop that:
1. Reads the sensed angular velocity and the time-varying target speed each step.
2. Applies motor torque to regulate speed and reject disturbances. A startup phase of {REGULATION_START_STEP} steps precedes the **regulation phase** in which mean speed error is scored (stall rules below still apply from step 0).
3. Avoids prolonged stall from the **first step onward** (not only during the regulation phase) and keeps mean tracking error within the stated threshold over the regulation phase.

- **Simulation length**: {MAX_STEPS} steps. Success requires a **full** run through all steps. Mean speed error is scored only on steps with step index \u2265 {REGULATION_START_STEP} (after startup); runs that end before that step index cannot succeed.
""",
    "success_criteria": f"""
## Success Criteria
1. **Speed Regulation**: Mean absolute deviation of the wheel's **true** instantaneous angular velocity from the commanded target during the regulation phase (after startup) must stay <= {MEAN_SPEED_ERROR_THRESHOLD} rad/s.
2. **No Stall**: From the start of the episode through the end, sustained **true** instantaneous angular speed below {STALL_SPEED_THRESHOLD} rad/s for {STALL_STEPS_THRESHOLD} or more consecutive steps counts as failure.

**Scoring vs. sensing**: Regulation and stall are judged on the **physical** wheel angular velocity each step. The documented angular-velocity API is your control feedback and may not match that physical value at the same simulation step. Optimize so the **actual** rotational state meets the criteria above.

## Design Constraints
- **APIs**: Use only the primitives documented below.
- **Sensing**: Use only the documented angular-velocity call for rotational speed feedback (do not derive speed from other object or joint state).
""",
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['C_06'].values()),
}
