"""
D-02: The Jumper task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'D_02' in _api_data and 'API_INTRO' in _api_data['D_02']:
    del _api_data['D_02']['API_INTRO']


TASK_PROMPT = {
    "task_description": """
Design a jumping mechanism to clear a pit and land on a distant platform by passing through multiple narrow slots.

## Task Environment
- **Platforms**: A left platform (start) and a right platform (target) separated by a wide pit.
- **Barriers**: Three vertical barriers with narrow horizontal slots (gaps) are positioned in the pit at approximately x ≈ 17 m, x ≈ 19 m, and x ≈ 21 m. Each barrier has a lower red bar and an upper red bar; the trajectory must pass through the vertical gap between them (jumper center must stay within the gap when crossing each barrier's x-range).
- **Pit Failure**: Jumper center must remain at y ≥ 0 m; below y = 0 m is considered in the pit and results in failure.
- **Build Zone**: x in [1.5, 6.5] m, y in [2.5, 5.5] m. All beam centers must be within this zone.
- **Beam Dimensions**: Each beam width and height is clamped by the environment to [0.1, 4.0] m.
- **Goal**: Reach the right platform (x >= 26.0m) by jumping from the left platform.

## Task Objective
Design a controller that:
1. Determines the optimal launch velocity (magnitude and direction) to jump over the pit.
2. Ensures the trajectory passes through the narrow gaps in all intermediate barriers.
3. Successfully lands on the right platform without falling into the pit or hitting the red sections of the barriers.
""",
    "success_criteria": """
## Success Criteria
1. **Target Reach**: Body reaches the right platform (x >= 26.0m, y >= 1.0m).
2. **Gap Clearance**: Trajectory successfully passes through all barrier slots without collision.

## Design Constraints
- **Mass Budget**: Total structure mass < 180 kg.
- **Pit Safety**: Jumper center y must be ≥ 0 m (below 0 m = failure).
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['D_02'].values()),
}
