"""
F-02: The Amphibian task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'F_02' in _api_data and 'API_INTRO' in _api_data['F_02']:
    del _api_data['F_02']['API_INTRO']


TASK_PROMPT = {
    "task_description": """
Design an amphibian vehicle to cross a body of water and reach the target bank.

## Task Environment
- **Water**: A 14m wide water gap between x=10m and x=24m.
- **Target**: Reach the right bank at x >= 26.0m.
- **Build Zone**: Vehicle must be built on the left bank in x=[2.0, 8.0], y=[0.0, 4.0].
- **Obstacles**: Three pillars are located in the water at x=14.0, 17.0, and 20.0m.
- **Environmental Factors**: Strong opposing current, quadratic water drag, and oscillating lateral winds.
- **Propulsion**: Use `apply_force()` for paddling. **Cooldown**: Each component has a 3-step cooldown between thrusts.

## Task Objective
Design a vehicle that:
1. Remains buoyant while crossing the water.
2. Uses effective propulsion (e.g., multiple paddles) to move forward against currents and headwinds.
3. Can steer or lift over pillars in the path.
4. Reaches the target bank.
""",
    "success_criteria": """
## Success Criteria
1. **Goal Reach**: Vehicle front reaches x >= 26.0m.
2. **Survival**: Vehicle does not sink (lowest point y < -0.5m).

## Design Constraints
- **Mass Budget**: Total structure mass <= 600 kg.
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['F_02'].values()),
}
