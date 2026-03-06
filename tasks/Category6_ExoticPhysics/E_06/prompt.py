"""
E-06: Cantilever Endurance task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'E_06' in _api_data and 'API_INTRO' in _api_data['E_06']:
    del _api_data['E_06']['API_INTRO']


TASK_PROMPT = {
    "task_description": """
Design a robust cantilever structure that remains intact under distance-scaled stochastic and moment-dominant impulsive loads.

## Task Environment
- **Support**: Ground anchors are allowed ONLY in the left support zone (x in [5.0, 6.5]m). You are limited to exactly ONE ground anchor.
- **Cantilever**: The structure must extend from the support zone to the right.
- **Loads**: The structure is subject to continuous noise and periodic "storms". Excitation intensity increases with distance from the support.
- **Momentum**: Periodic coherent pulses create significant overturning moments, especially at the structure's tip.
- **Build Zone**: x in [5.0, 15.0] m, y in [1.5, 8.0] m. Note that a small "forbidden zone" exists near x=10 where beam centers are rejected.
- **Goal**: Maintain structural integrity (avoid joint failure or beam destruction) for the duration of the test while spanning the required horizontal distance.

## Task Objective
Design a cantilever that:
1. Anchors to the ground at exactly one point within x=[5.0, 6.5].
2. Spans from the support to at least x=13.0m and reaches a height of y=5.0m.
3. Withstands distance-scaled vibration and impulsive moments without any part of the structure breaking or being destroyed.
""",
    "success_criteria": """
## Success Criteria
1. **Integrity**: The structure remains entirely intact; no joints break and no beams are destroyed.
2. **Span**: Structure reaches at least x <= 7.0m (near support) and x >= 13.0m (tip), and a height of y >= 5.0m.
3. **Efficiency**: Meets requirements within the mass limit (120 kg).

## Design Constraints
- **Anchor Limit**: Exactly 1 ground anchor.
- **Mass Budget**: Total structure mass <= 120 kg.
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['E_06'].values()),
}
