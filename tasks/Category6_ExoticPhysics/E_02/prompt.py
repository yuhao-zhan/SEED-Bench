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


TASK_PROMPT = {
    "task_description": """
Design a controller for a craft navigating through a high-friction, "thick air" environment.

## Task Environment
- **Craft**: A vehicle subject to intense drag and heating.
- **Goal**: Reach a target coordinate while managing internal heat levels.
- **Heat**: Applying thrust increases craft heat. Overheating causes mission failure.

## Task Objective
Design a control loop that:
1. Navigates the craft toward the target position.
2. Monitors heat levels and manages thrust to avoid overheating.
3. Successfully reaches the target within simulation time limits.
""",
    "success_criteria": """
## Success Criteria
1. **Target Reach**: Craft reaches the target position.
2. **Thermal Safety**: Craft does not overheat during the mission.

## Design Constraints
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['E_02'].values()),
}
