"""
K-02: The Climber task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'K_02' in _api_data and 'API_INTRO' in _api_data['K_02']:
    del _api_data['K_02']['API_INTRO']

task_data = _api_data['K_02']
if 'API_INTRO' in task_data:
    del task_data['API_INTRO']

TASK_PROMPT = {
    'task_description': """
Design a 2D climber mechanism that can scale a vertical wall using motor-driven segments and adhesive pads.

## Task Environment
- **Vertical Wall**: A surface on the right side of the build zone. Wall height is 30 m; wall friction coefficient is 1.0 (for grip).
- **Build Zone**: x=[0, 5], y=[0, 25]. All structure components must be placed within this zone.
- **Wall Contact**: During motion, the climber must remain within x=[3.5, 7.5]m to maintain wall contact (evaluation fails otherwise).
- **Ground / Fall**: Evaluation fails if the climber's altitude falls below 0.5 m (indicating total structural collapse).
- **Starting Position**: Agent components should be centered around x=4.5m, y=1.5m.
- **Target**: Move the climber to at least y=20.0m. Evaluation uses the position of the first body you create (designate it as your main climbing body).

## Constraints (must satisfy)
- **Adhesion**: Use `add_pad` and `set_pad_active` to stick to the wall. Active pads provide strong adhesive force to maintain wall contact.
- **Motion**: The climber must maintain active upward motion for at least 10.0 seconds.
- **Mass Budget**: Total structure mass must be at least 0 kg and at most 50 kg.
- **Build Zone**: All components must stay within x=[0, 5], y=[0, 25] at initialization.
- **Beam Dimensions**: 0.05 <= width, height <= 3.0 meters.
- **Pad Radius**: 0.05 <= radius <= 0.25 meters (for `add_pad`).
- **Pivot Joint Limits**: Angle limits for pivot joints are clamped to [-π, π] radians.
- **Joint strength**: Maximum joint reaction force and maximum joint torque are unlimited in the default environment (joints do not break).

## Instructions
1. **Design**: Create a climber structure (e.g., using alternating pads and rotating legs).
2. **Control**: Use `set_motor` on pivot joints and `set_pad_active` on pads in `agent_action` to climb.
""",
    
    'success_criteria': """
## Success Criteria
1. **Vertical Movement**: Reaches y >= 20.0m.
2. **Locomotion**: Maintains active motion for >= 10.0 seconds.
3. **Stability**: Structure remains within build zone and mass limits.
- **Build zone**: All components must stay within x=[0, 5], y=[0, 25] at initialization.

## Design Constraints
- **Mass Budget**: Minimum 0 kg, maximum at most 50 kg.
- **APIs**: Use only the primitives documented below.
""",
    
    'primitives_api': API_INTRO + '\n\n' + '\n\n'.join(task_data.values()),
}
