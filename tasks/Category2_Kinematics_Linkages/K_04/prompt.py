"""
K-04: The Pusher task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO
import sys

# Add tasks directory to path to import primitives_api
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'K_04' in _api_data and 'API_INTRO' in _api_data['K_04']:
    del _api_data['K_04']['API_INTRO']

task_data = _api_data['K_04']
if 'API_INTRO' in task_data:
    del task_data['API_INTRO']

TASK_PROMPT = {
    'task_description': """
Design a ground-based pusher vehicle that can move a heavy object across a high-friction surface.

## Task Environment
- **Ground**: A high-friction horizontal surface at y=1.0m.
- **Heavy Object**: A rectangular block (approximately 50 kg) at x=8.0m.
- **Build Zone**: x=[0, 15], y=[1.5, 8]. All structure components must be placed within this zone.
- **Target**: Push the object to at least x=18.0m (10 meters forward from starting x).

## Constraints (must satisfy)
- **Distance**: The object center reaches x >= 18.0m.
- **Motion**: The pusher must maintain forward motion for at least 12.0 seconds.
- **Mass Budget**: Total structure mass must be less than 40 kg.
- **Build Zone**: All components must stay within x=[0, 15], y=[1.5, 8].
- **Beam Dimensions**: 0.05 <= width, height <= 3.0 meters.
- **Wheel Radius**: 0.05 <= radius <= 0.8 meters (for add_wheel).
- **Pivot Joint Angle Limits**: Radians in [-π, π] when using limits on pivot joints.
- **Stability**: Pusher chassis tilt must stay within ±30° (π/6 rad); excess tilt is failure.
- **Payload Support**: Object must remain on the platform; object center y below 0.5 m is failure.

## Instructions
1. **Design**: Create a wheeled or sliding pusher vehicle.
2. **Control**: Use `set_motor` on pivot joints (wheels) or apply forces/torques to drive the vehicle.
""",
    
    'success_criteria': """
## Success Criteria
1. **Movement**: Object reaches x >= 18.0m.
2. **Locomotion**: Maintains active motion for >= 12.0 seconds.
3. **Stability**: Structure remains intact and within constraints.

## Design Constraints
- **Mass Budget**: < 40 kg.
- **APIs**: Use only the primitives documented below.
""",
    
    'primitives_api': API_INTRO + '\n\n' + '\n\n'.join(task_data.values()),
}
