"""
E-02: The Thick Air task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'E_02' in _api_data and 'API_INTRO' in _api_data['E_02']:
    del _api_data['E_02']['API_INTRO']

# Time budget (10000) in task_description must match Sandbox.MAX_STEPS in environment.py.
TASK_PROMPT = {
    "task_description": """
Design a controller for a craft navigating through a complex "thick air" environment.

## Task Environment
- **Craft**: A vehicle subject to intense drag, momentum drain, and thermal constraints. The craft starts at position (x=8.0 m, y=2.0 m).
- **Terrain**: The path contains narrow gates that the craft must pass through. The craft center must stay within the following gate clearances to avoid collision:
  - **Gate 1**: x in [12.0, 14.0] m, y in [1.0, 2.8] m.
  - **Gate 2**: x in [22.0, 24.0] m, y in [1.8, 3.0] m.
- **Anomalies**:
  - **High-Drag Atmosphere**: Intense air resistance affects terminal velocity.
  - **Momentum Drain Zones**: Specialized regions that rapidly sap the craft's kinetic energy.
  - **Slippery Zones**: Regions where resistive forces bias the craft's motion.
  - **Oscillating Winds**: Localized atmospheric disturbances that apply periodic vertical forces.
- **Goal**: Reach a target coordinate (x in [28.0, 32.0], y in [2.0, 5.0]) while managing internal heat.
- **Heat**: Applying thrust increases craft heat. The overheat limit is 72000 N·s; exceeding it causes mission failure.
- **Time budget**: You have at most 10000 simulation steps to reach the target.

## Task Objective
Design a control loop that:
1. Navigates the craft toward the target position, passing through gate clearances.
2. Compensates for local physical anomalies (drain, slip, wind) as they are encountered.
3. Monitors heat levels and manages thrust to avoid reaching the overheat limit.
""",
    "success_criteria": """
## Success Criteria
1. **Target Reach**: Craft center enters the target zone.
2. **Thermal Safety**: Craft heat stays below the overheat limit (72000 N·s).

## Design Constraints
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['E_02'].values()),
}
