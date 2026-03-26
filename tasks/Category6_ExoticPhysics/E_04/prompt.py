"""
E-04: Variable Mass task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'E_04' in _api_data and 'API_INTRO' in _api_data['E_04']:
    del _api_data['E_04']['API_INTRO']


TASK_PROMPT = {
    "task_description": """
Design a complex structure that remains intact under sinusoidally varying mass and environmental vibration.

## Task Environment
- **Mass Variation**: Every beam's mass varies over time according to multiple frequency components.
- **Base Excitation**: The ground support undergoes periodic vertical and horizontal oscillation.
- **Fatigue**: Joint strength (force and torque limits) decays exponentially over time with a time constant of 100.0 s.
- **Joint Limits (nominal)**: Joints fail if reaction force exceeds 6.0 N or reaction torque exceeds 10.0 N·m (before fatigue decay).
- **Beam Size**: Each beam dimension (width, height) is clamped by the environment to [0.1, 4.0] m.
- **Build Zone**: x in [5.0, 15.0] m, y in [1.5, 8.0] m.
- **Simulation**: The run lasts 12,000 simulation steps. Success is evaluated at the end of the run; the structure must remain intact for the full simulation.
- **Goal**: Maintain structural integrity until the end of the simulation.

## Task Objective
Design a structure that:
1. Spans from x=6.0m to x=14.0m.
2. Uses at least 5 beams and 6 joints.
3. Includes at least one pivot (revolute) joint.
4. Withstands the varying inertial loads and base vibration without breaking any joints.
""",
    "success_criteria": """
## Success Criteria
1. **Integrity**: All joints remain intact throughout the simulation.
2. **Span**: Structure spans from at least x <= 6.0m to x >= 14.0m.
3. **Complexity**: Meets the minimum beam (5) and joint (6) counts.
4. **Variety**: At least one joint must be a pivot (`type='pivot'`).

## Design Constraints
- **Mass Budget**: Total structure mass (instantaneous) must remain within the limit (default 400 kg).
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['E_04'].values()),
}
