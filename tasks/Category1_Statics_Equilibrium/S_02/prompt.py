"""
S-02: The Skyscraper task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'S_02' in _api_data and 'API_INTRO' in _api_data['S_02']:
    del _api_data['S_02']['API_INTRO']


TASK_PROMPT = {
    'task_description': """
Build a tall tower on a narrow foundation that must survive an earthquake and strong wind.
You may consider structural damping to counteract vibrations.

## Task Environment
- **Foundation**: A static ground area at x=[-2, 2], y=0. Your structure can only contact the ground within this narrow zone.
- **Earthquake**: After an initial period, the foundation will undergo horizontal oscillations. The foundation itself moves, and your structure must survive the vibrations.
- **Wind**: Lateral forces are applied to structural components at higher altitudes, simulating wind pressure.
- **Beam Dimensions**: 0.1 <= width, height <= 10.0 meters.

## Task Objective
Design a stable skyscraper structure that can:
1. Reach an initial height greater than 30m.
2. Maintain its integrity and height during and after the earthquake.
3. Resist lateral wind forces at high altitudes.
4. Maintain global stability (the structure's center of mass must remain within a safe lateral range).
""",
    
    'success_criteria': """
## Success Criteria
1. **Height**: Topmost point > 30m at start.
2. **Survival**: Structure remains standing (top point remains > 5m) after the earthquake and wind duration.
3. **Stability**: Global center of mass stays within x=[-300, 300] relative to foundation.

## Design Constraints
- **Foundation Contact**: All ground contact must be within x=[-2, 2].
- **Height Requirement**: Must exceed 30m.
- **Width Limit**: Total structure width cannot exceed 12m.
- **APIs**: Use only the primitives documented below.
""",
    
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['S_02'].values()),
}
