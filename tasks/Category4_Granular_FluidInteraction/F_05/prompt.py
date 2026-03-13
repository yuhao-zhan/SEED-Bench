"""
F-05: The Boat task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'F_05' in _api_data and 'API_INTRO' in _api_data['F_05']:
    del _api_data['F_05']['API_INTRO']


TASK_PROMPT = {
    "task_description": """
Design a stabilization and containment structure for a boat in rough water.

## Task Environment
- **Boat**: A platform floating in water (x around 15m, y around 2.5m).
- **Cargo**: 10 granular particles loaded onto the boat.
- **Obstacles**: Static rocks are present in the water which can strike the boat or cargo.
- **Dynamic Forces**: The boat is subject to multi-mode waves, sudden gusts, lateral wind, and water currents.
- **Build Zone**: Structure must be attached to the boat body within x=[12.0, 18.0], y=[2.0, 4.5].

## Task Objective
Design a structure that:
1. Prevents all cargo from falling overboard despite severe vessel motion.
2. Lowers the center of mass or provides stabilization to prevent the boat from capsizing.
3. Withstands the impact of periodic rogue waves and lateral impulses.
""",
    "success_criteria": """
## Success Criteria
1. **Cargo Retention**: All initial cargo (100%) remains on the boat. Cargo is counted as lost (in water) if its center falls below y = 1.98 m.
2. **Stability**: Boat does not capsize (angle must remain below 18 degrees).

## Design Constraints
- **Mass Budget**: Total structure mass <= 60 kg.
- **Beam dimensions**: Each beam width and height is clamped by the environment to [0.1, 1.0] m (see Add Beam in the API below).
- **Joint structural limits**: In the base environment, joints are not subject to a documented force/torque limit; in some task variants, joints may fail if reaction forces or torques exceed the environment's structural capacity.
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['F_05'].values()),
}
