"""
D-01: The Launcher task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'D_01' in _api_data and 'API_INTRO' in _api_data['D_01']:
    del _api_data['D_01']['API_INTRO']


TASK_PROMPT = {
    "task_description": """
You need to design a launcher that propels a projectile to hit a distant target.

## Task Environment
- **Ground**: Flat surface at y=0 to y=1 m.
- **Build Zone**: x=[5, 15] m, y=[1.5, 8] m. All beam centers and anchors must lie inside this zone.
- **Projectile**: A ball (radius 0.25 m) starts at rest at position (10, 3) m. Your launcher must accelerate it toward the target.
- **Target Zone**: x from 40 m to 45 m, and y from 2 m to 5 m. Success requires the projectile center to be inside this rectangle.

## Task Objective
Design a launcher that:
1. Uses levers, whip-like motion, and/or spring energy storage to propel the projectile.
2. Launches the projectile so that it reaches and hits the target zone.
3. Stays within the build zone and material budget.
""",
    "success_criteria": """
## Success Criteria
1. **Hit**: Projectile center must lie inside the red target zone (x in [40, 45] m, y in [2, 5] m).
2. **No early failure**: Projectile must not be destroyed or leave the simulation bounds.

## Design Constraints
- **Mass Budget**: Total structure mass < 500 kg.
- **Beam dimensions**: Each beam width and height must be in [0.1, 5.0] m (enforced by the environment).
- **Spring stiffness**: Spring stiffness must be in [10, 3000] N/m (enforced by the environment).
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['D_01'].values()),
}
