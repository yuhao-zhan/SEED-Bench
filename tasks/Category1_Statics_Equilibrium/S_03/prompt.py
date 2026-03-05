"""
S-03: The Cantilever task Prompt and Primitives definition
"""

import json
import os

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)


TASK_PROMPT = {
    'task_description': """
Construct a horizontal cantilever structure anchored ONLY to the left wall. 
The structure must extend as far right as possible and support multiple heavy vertical payloads.

## Task Environment
- **Wall**: A vertical static surface at x=0. You may use a maximum of 2 anchor points on this wall. Note that some sections of the wall may be unsuitable for anchoring or exhibit varying structural strength.
- **Payloads**: Multiple significant weights will be applied to your structure at different times (e.g., at t=5s and t=15s). Payloads may be attached directly or dropped from height as dynamic impacts.
- **Atmosphere**: The environment may exhibit high gravity or lateral wind forces that test structural stiffness.
- **Obstacles**: Static obstructions may be present, requiring your structure to navigate through specific clearances.

## Task Objective
Design a robust cantilever structure that can:
1. Extend horizontally from the wall to reach the target distance.
- **Goal**: Reach x >= 12.0m.
2. Support all applied payloads (stationary or dynamic) for 10 seconds each without collapsing.
3. Manage internal stresses so that the wall anchors do not exceed their structural strength.
4. **Stiffness**: Maintain vertical stability. Excessive sag will result in failure.
- **Mass Limit**: < 15,000 kg.
""",
    
    'success_criteria': """
## Success Criteria
1. **Reach**: Structure reaches the required horizontal distance (Tip reaches x >= 12.0m).
2. **Load Bearing**: Successfully supports all payloads for the 10s test duration.
3. **Anchor Integrity**: All wall anchors remain intact (no breakage due to excessive force/torque).
4. **Stability**: The structure does not sag below the allowed vertical threshold.

## Design Constraints
- **Mass Budget**: < 15,000 kg.
- **Anchor Limit**: Maximum 2 anchor points on the wall.
- **Strength Limits**: Wall joints have finite capacity; excessive torque will cause them to snap.
- **Geometry**: The structure must reach the target and provide suitable nodes for payload attachment.
- **APIs**: Use only the primitives documented below.
""",
    
    'primitives_api': '\n\n'.join(_api_data['S_03'].values()),
}
