"""
C-06: The Governor task Prompt and Primitives definition
"""

import json
import os

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)


TASK_PROMPT = {
    "task_description": """
Design a controller (a "governor") to maintain a wheel's rotation at a constant target speed despite varying external loads.

## Task Environment
- **Wheel**: A circular body that can rotate around its center.
- **Motor**: Provides torque to the wheel to control its speed.
- **Target Speed**: The wheel must be maintained at a target speed (e.g., 3.0 rad/s). Note: The target speed is dynamic and may change during the run; use the API to query the current target each step.
- **External Loads**: The wheel is subject to multiple types of resisting torque:
  1. **Constant Drag**: A baseline resistance.
  2. **Step Load**: A sudden, sustained increase in resisting torque occurring at a specific time.
  3. **Periodic Disturbances**: Time-varying oscillations in the load.
  4. **Nonlinearities**: The system may exhibit cogging torque or stiction at low speeds.

## Task Objective
Design a control loop that:
1. Observes the current angular velocity and the time-varying target speed.
2. Applies motor torque to regulate the wheel speed and reject disturbances. There is a brief initial startup phase (1000 steps) allowed for the system to reach the target speed before regulation quality is evaluated.
3. Successfully prevents the wheel from stalling or deviating significantly from the target speed for a sustained period.
""",
    "success_criteria": """
## Success Criteria
1. **Speed Regulation**: Mean speed error during the regulation phase (after startup) remains within a tight threshold (e.g., < 0.23 rad/s).
2. **No Stall**: The wheel must not stall (speed must remain above a minimum threshold like 0.3 rad/s) for any sustained period.

## Design Constraints
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': '\n\n'.join(_api_data['C_06'].values()),
}
