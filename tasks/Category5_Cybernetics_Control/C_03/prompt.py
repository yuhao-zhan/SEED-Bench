"""
C-03: The Seeker (Very Hard) task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'C_03' in _api_data and 'API_INTRO' in _api_data['C_03']:
    del _api_data['C_03']['API_INTRO']


TASK_PROMPT = {
    "task_description": """
Design a controller for a seeker craft to achieve multiple heading-aligned rendezvous with a dynamic target.

## Task Environment
- **Seeker**: A craft with a SINGLE thrust vector; thrust is applied only along its current heading. Heading turns at a limited rate toward the commanded direction.
- **Sensing**: `get_target_position()` has variable delay, blind zones, and only updates periodically. You must infer target velocity from position history.
- **Activation Gate**: Rendezvous only counts after the seeker "activates" by staying in the zone x in [13.0, 17.0] m for at least 80 consecutive steps.
- **Moving Corridor**: The seeker must stay within time-varying horizontal bounds. Leaving the corridor fails the run.
- **Wind & Obstacles**: Dynamic wind forces and moving obstacles exist in the corridor.
- **Fuel**: Total thrust impulse is limited; fuel-efficient trajectories are required.

## Task Objective
Design a multi-phase control strategy:
1. **Activation**: Position and hold the seeker in the activation zone until activated.
2. **Slotted Rendezvous**: Achieve two separate rendezvous in narrow time slots (periodic slots occur within the windows [3700, 4800] and [6200, 7300]). Rendezvous only counts within the central region (x in [10.0, 20.0] m).
   - Rendezvous requires: getting close (< 6.0m), matching velocity (rel speed < 1.8 m/s), AND aligning seeker heading with the target's movement direction.
3. **Tracking**: Maintain a close distance to the target after the second rendezvous.
""",
    "success_criteria": """
## Success Criteria
1. **Rendezvous Completion**: Successfully achieve rendezvous in both phase 1 and phase 2 time slots (within the central region) with correct heading alignment.
2. **Tracking**: Maintain distance <= 8.5 m from target after the second rendezvous until the end.
3. **Safety**: No collisions with obstacles; stay within the moving corridor.
4. **Efficiency**: Complete the task within the impulse budget.

## Design Constraints
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['C_03'].values()),
}
