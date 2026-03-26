"""
E-03: The Sled task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'E_03' in _api_data and 'API_INTRO' in _api_data['E_03']:
    del _api_data['E_03']['API_INTRO']


TASK_PROMPT = {
    "task_description": """
Design a controller for a sled to navigate through a low-friction environment and pass through checkpoints.

## Task Environment
- **Sled**: A sliding body subject to thrust and minimal friction. It starts at position (x=8.0 m, y=2.0 m).
- **Checkpoints** (must be passed in order):
  - **First checkpoint (Alpha)**: Sled center must enter the zone x in [17.5, 19.0] m, y in [3.8, 4.5] m.
  - **Second checkpoint (Beta)**: Sled center must enter the zone x in [23.0, 24.5] m, y in [2.5, 3.2] m.
- **Momentum Drain Zone**: Between x=11.0 m and x=17.0 m, the sled experiences a continuous loss of momentum.
- **Wind Zone**: Between x=14.0 m and x=28.0 m, the sled is subject to external vertical forces (wind).
- **Thrust Scaling Zone**: Between x=19.5 m and x=21.0 m, the efficiency of the propulsion system is significantly reduced.
- **Horizontal Thrust Reverse Zone**: Between x=20.0 m and x=25.0 m, horizontal thrust is significantly altered.
- **Oscillating Force Zone**: Between x=21.0 m and x=27.0 m, the sled is subject to periodic horizontal external forces.
- **Speed Penalty Zone**: Between x=22.0 m and x=26.0 m, a speed limit of 4.0 m/s is enforced; exceeding this threshold triggers anomalous behavior.
- **Vertical Thrust Reverse Zone**: Between x=26.5 m and x=28.5 m, vertical thrust is significantly altered.
- **Final target**: Sled center must enter the zone x in [28.0, 32.0] m, y in [2.2, 2.8] m.
- **Time limit**: The task must be completed within 10,000 simulation steps; the run terminates after this limit and failure is declared if the objective is not met by then.
""",
    "success_criteria": """
## Success Criteria
1. **Checkpoint Completion**: Sled passes through both required checkpoints in order (Alpha, then Beta).
2. **Target Reach**: Sled center enters the final target zone (x in [28.0, 32.0], y in [2.2, 2.8]).
3. **Efficiency**: Reaches the final target within 10,000 simulation steps.

## Design Constraints
- **Speed Limit**: Maintain speed below 4.0 m/s while in the penalty zone (x in [22.0, 26.0]) to avoid significant momentum loss.
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['E_03'].values()),
}
