"""
D-03: Phase-Locked Gate task Prompt and Primitives definition
"""

import json
import os

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)


TASK_PROMPT = {
    "task_description": """
Design an attachment for a cart to help it pass through multiple rotating gates at precise moments.

## Task Environment
- **The Cart**: A cabin starts at x=4.0m, y=2.5m with an initial horizontal speed of 10.0m/s.
- **Rotating Gates**: Four gates with rotating rods are located at x=10.0, 11.5, 11.75, and 12.5. Each gate is only 'open' (passable) during a very narrow angular window.
- **Obstacles**: Mud zones, impulse zones (providing backward kicks), and decel zones affect the cart's velocity profile along the track.
- **Build Zone**: x=[4.8, 9.0] m, y=[2.0, 3.2] m. All beams must be attached to the cart cabin.
- **Success Criteria**: The cart must reach the target zone (x >= 11.75m) with a final speed between 0.45m/s and 2.6m/s, having passed all four gates when they were open.

## Task Objective
## Task Objective
Design an attachment that:
1. Uses a specific number of beams (between 4 and 5) to adjust the cart's mass and momentum.
2. Carefully tunes the cart's arrival time at each gate to match the 'open' phase.
3. Successfully passes the rotating gates and reaches the target distance.
...
## Success Criteria
1. **Gate Clearance**: Pass all four rotating gates without collision (only when open).
2. **Target**: Reach x >= 11.75m with final speed in [0.45, 2.6] m/s.


## Design Constraints
- **Beam Count**: Exactly 4 or 5 beams must be used.
- **Mass Budget**: Total structure mass < 14.0 kg.
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': '\n\n'.join(_api_data['D_03'].values()),
}
