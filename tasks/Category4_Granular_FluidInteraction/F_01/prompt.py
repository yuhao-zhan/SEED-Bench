"""
F-01: The Dam (extreme) task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'F_01' in _api_data and 'API_INTRO' in _api_data['F_01']:
    del _api_data['F_01']['API_INTRO']


TASK_PROMPT = {
    "task_description": """
Design a free-standing dam to block water particles in an extreme environment.

## Task Environment
- **Water Particles**: 300 particles in a reservoir.
- **Surge Events**: Nine surge waves of increasing intensity will push the water.
- **Debris**: Heavy debris will impact the dam at regular intervals.
- **Build Zone**: Three disjoint narrow vertical strips: x=[12.4, 12.6], [12.9, 13.1], and [13.4, 13.6]. Max height y=7.5m.
- **Constraint**: Mandatory underflow gap; no beams allowed below y=0.5m.
- **Constraint**: ZERO floor anchors; the dam must be free-standing.
- **Constraint**: Maximum beam height is 1.5 m.
- **Constraint**: Middle build strip [12.9, 13.1] must contain at least 1 but at most 1 beam (forces bridge topology).

## Task Objective
Design a structure that:
1. Blocks water particles such that the leakage rate remains below 0.10%.
2. Maintains structural integrity under surge and debris impact (welds can break).
3. Fits within narrow build strips and respects the underflow requirement.
""",
    "success_criteria": """
## Success Criteria
1. **Leakage Rate**: Total leakage < 0.10%.
2. **Integrity**: Structure does not collapse; all beams must remain connected (no broken joints).

## Design Constraints
- **Mass Budget**: Total structure mass <= 380 kg.
- **Beam Limit**: Maximum 18 beams.
- **Joint Limit**: Maximum 15 beam-to-beam joints.
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['F_01'].values()),
}
