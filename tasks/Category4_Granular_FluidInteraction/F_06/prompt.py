"""
F-06: The Pipeline (hard) task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'F_06' in _api_data and 'API_INTRO' in _api_data['F_06']:
    del _api_data['F_06']['API_INTRO']


TASK_PROMPT = {
    "task_description": """
Design a transport system to route fluid particles to a narrow target zone while avoiding environmental hazards.

## Task Environment
- **Fluid**: A batch of 60 small fluid particles released from a source container.
- **Target Zone**: x in [18, 22] m, y in [0, 1.5] m.
- **Hazards**: Pits may exist in the corridor; particles entering them are lost.
- **Build Zone**: x=[6, 18] m, y=[0, 6] m.
- **Control**: You can apply forces directly to particles using `apply_force_to_particle()`.

## Task Objective
Design a system (structure and control) that:
1. Directs at least 90% of released fluid particles into the target zone.
2. Navigates particles safely over any pits or obstacles.
3. Operates within a per-step force budget and total structure mass limit.
""",
    "success_criteria": """
## Success Criteria
1. **Delivery Efficiency**: At least 90% of released particles reach the target zone.
2. **Resource Management**: Per-step force usage must not exceed 12000 N per step.

## Design Constraints
- **Mass Budget**: Total structure mass <= 380 kg.
- **Force Budget**: 12000 N per step.
- **Anchoring**: The structure must be anchored to the ground using at least one joint.
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['F_06'].values()),
}
