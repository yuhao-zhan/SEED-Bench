"""
C-01: Cart-pole balance task (pole starts upright) — prompt and primitives definition.
"""

import importlib.util
import json
import os
import re
import sys

# Load C_01 environment constants without package import path issues
_env_path = os.path.join(os.path.dirname(__file__), "environment.py")
_spec = importlib.util.spec_from_file_location("c01_environment", _env_path)
_c01_environment = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_c01_environment)
CART_FORCE_LIMIT_NEWTONS = _c01_environment.CART_FORCE_LIMIT_NEWTONS
_fn = int(CART_FORCE_LIMIT_NEWTONS) if float(CART_FORCE_LIMIT_NEWTONS).is_integer() else CART_FORCE_LIMIT_NEWTONS

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'C_01' in _api_data and 'API_INTRO' in _api_data['C_01']:
    del _api_data['C_01']['API_INTRO']

# Keep APPLY_CART_FORCE clamp in JSON aligned with environment.CART_FORCE_LIMIT_NEWTONS
_clamp_bracket = re.compile(r"\[-\d+(?:\.\d+)?,\s*\d+(?:\.\d+)?\]")
for _k, _v in list(_api_data.get('C_01', {}).items()):
    if isinstance(_v, str) and _k == "APPLY_CART_FORCE" and _clamp_bracket.search(_v):
        _api_data['C_01'][_k] = _clamp_bracket.sub(f'[-{_fn}, {_fn}]', _v, count=1)


TASK_PROMPT = {
    "task_description": f"""
Design a controller to maintain a pole balanced on a moving cart.

## Task Environment
- **Cart**: A body of mass 10 kg and dimensions 1.0m (width) x 0.5m (height) that moves along a horizontal track at y=2.0m (center x=10m, safe range ±8.5m inclusive).
- **Pole**: Mass 1 kg, width 0.2m. Initially upright (angle = 0° or 0rad). **Length**: 2.0m.
- **Actuator Limit**: The cart force is limited to ±{_fn}N.
- **Sensor reporting (angle)**: 0 simulation steps of delay from true state.
- **Sensor reporting (angular velocity)**: 0 simulation steps of delay from true state.
- **Goal**: Maintain the pole in the upright position (|angle| <= 45°) for at least 200 consecutive steps. **Scoring**: After that lock-in, the episode does not end early solely because |angle| exceeds 45°, until the pole passes horizontal (|angle| > 90°), you leave the track, or you hit the step limit. **Final success** still requires |angle| <= 45° at the last step.
- **Grading vs sensors**: All angle conditions above (45°, 90°, lock-in count, and terminal check) use the simulator’s **true** pole state. Values from `get_pole_angle` / `get_pole_angular_velocity` follow the **Sensor reporting** delays above and may therefore differ from the state used for scoring—design accordingly.
- **Episode length**: At most 20000 simulation steps (must hold balance until the end).
- **Time Step**: Exactly **1/60** seconds per simulation step (same as the environment integration step).

## Task Objective
Design a control strategy:
1. **Balance**: Achieve 200 consecutive steps with |angle| <= 45°, keep the cart within track limits, and end the episode with |angle| <= 45° (see **Goal** for mid-episode rules after lock-in).
2. Observe state through the documented APIs; remember scoring uses **true** pole angles as stated under **Grading vs sensors**.
""",
    "success_criteria": f"""
## Success Criteria
1. **Stability**: Pole is held within the upright region (|angle| <= 45°) for at least 200 consecutive steps, where **|angle| is the simulator’s true pole angle** (which may differ from `get_pole_angle` when **Sensor reporting (angle)** delay is non-zero). After lock-in, early termination is only for track exit, time limit, or |angle| > 90°; **final** success requires |angle| <= 45° when the episode ends.
2. **Track Limits**: Cart remains within the safe zone (|x - 10| ≤ 8.5m).
3. **Episode length**: At most 20000 steps.

## Design Constraints
- **Actuator**: Cart force must not exceed ±{_fn}N.
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['C_01'].values()),
}
