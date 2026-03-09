"""
S-03: The Cantilever task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'S_03' in _api_data and 'API_INTRO' in _api_data['S_03']:
    del _api_data['S_03']['API_INTRO']


TASK_PROMPT = {
    'task_description': """
Construct a horizontal cantilever structure anchored ONLY to the left wall at x=0. 
The structure must extend horizontally to reach the target distance and support multiple heavy vertical payloads applied at different times (e.g., at t=5s and t=15s).

## Task Environment
- **Wall**: A vertical static surface at x=0. You may use a maximum of 2 anchor points on this wall.
- **Payloads**: Payloads will be applied to your structure to test its load-bearing capacity and stability.
- **Atmosphere**: The environment exhibits physical properties that will test the structural integrity of your design.
- **Obstacles**: The build zone may contain static obstructions that your structure must navigate.

## Task Objective
Design a robust cantilever structure that can:
1. Extend horizontally from the wall to reach the target distance.
- **Goal**: Reach x >= 12.0m.
2. Support all applied payloads for 10 seconds each without collapsing or excessive sagging.
3. Manage internal stresses so that the wall anchors and structural joints remain intact.
- **Mass Limit**: < 15,000 kg.
""",
    
    'success_criteria': """
## Success Criteria
1. **Reach**: Structure reaches the required horizontal distance (Tip reaches x >= 12.0m).
2. **Load Bearing**: Successfully supports all payloads for the 10s test duration.
3. **Anchor Integrity**: All wall anchors and joints remain intact.
4. **Stability**: The structure does not sag below the allowed vertical threshold.

## Design Constraints
- **Mass Budget**: < 15,000 kg.
- **Anchor Limit**: Maximum 2 anchor points on the wall.
- **Strength Limits**: Joints and anchors have finite capacity; exceeding these limits will cause failure.
- **APIs**: Use only the primitives documented below.
""",
    
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['S_03'].values()),
}
