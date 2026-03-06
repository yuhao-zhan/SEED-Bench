"""
C-05: The Logic Lock task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'C_05' in _api_data and 'API_INTRO' in _api_data['C_05']:
    del _api_data['C_05']['API_INTRO']


TASK_PROMPT = {
    "task_description": """
Design a controller for an agent to trigger a "Logic Lock" by activating switches in a strict temporal and spatial sequence.

## Task Environment
- **Switches**: Three switches (A, B, C) located at specific coordinates.
- **Sequence**: Switches must be triggered in the order A -> B -> C.
- **Temporal Windows**: 
  - To trigger B, it must be visited within a short time window after A is triggered.
  - To trigger C, it must be visited after B, with a specific cooldown period between triggers.
- **Spatial Constraints**: Some switches (e.g., C) may only trigger if approached from a specific height or direction.
- **Gate**: A barrier opens only after specific sequence milestones are met.

## Task Objective
Design a control loop that:
1. Navigates to switch A to begin the sequence.
2. Quickly moves to switch B within the allowed temporal window.
3. Respects cooldowns and spatial requirements to trigger switch C and unlock the final gate.
4. Uses feedback to discover exact timing and height requirements.
""",
    "success_criteria": """
## Success Criteria
1. **Sequence Completion**: Switches A, B, and C triggered in the correct order and within their respective temporal/spatial windows.
2. **Efficiency**: Full sequence completed and final gate cleared within the time limit.

## Design Constraints
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['C_05'].values()),
}
