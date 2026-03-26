"""
S-01: The Bridge task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'S_01' in _api_data and 'API_INTRO' in _api_data['S_01']:
    del _api_data['S_01']['API_INTRO']


TASK_PROMPT = {
    'task_description': """
Design a static bridge to connect two cliffs. A vehicle will spawn on the left cliff and attempt to cross to the right.

## Task Environment
- **Cliffs**: Two static platforms separated by a wide gap. Friction coefficient: 0.8.
- **Left Cliff**: Ends at x=10.0m, y=10.0m.
- **Right Cliff**: Starts at x=25.0m, y=10.0m.
- **Vehicle**: A motorized vehicle (mass: 2000.0 kg) will spawn on the left cliff at x=5.0 m, y=11.05 m and move right at a constant velocity of 5.0 m/s. Vehicle footprint: wheelbase 3.0 m, chassis 2.0 m × 0.5 m, wheel radius 0.4 m. Friction coefficient: 0.8.
- **Fail Zone**: A water surface exists at y=0m. The task fails if the vehicle or any structural component reaches or goes below y=0.5 m.
- **Target**: The vehicle must fully cross the gap and reach at least x=30.0m on the right side.
- **Material Defaults**: The default restitution for structural components is 0.2 unless modified.

## Task Objective
Design a stable bridge structure that can:
1. Span the gap and connect the two cliffs.
2. Support the dynamic load of the heavy vehicle as it crosses.
3. Provide a continuous and smooth deck surface for the vehicle's wheels.
4. Maintain structural integrity under load. Joints have strength limits; excessive force or torque will cause them to break.

## Constraints (must satisfy)
- **Mass Budget**: Total structure mass must be less than 2000 kg.
- **Build Zone**: Structure must be built within x=[10, 30], y=[5, 15] (the upper x-bound is the target position so the deck can reach the goal).
- **Beam Dimensions**: 0.1 <= width, height <= 10.0 meters.
- **Traction**: The deck surface must provide a minimum friction coefficient of 0.5 for the vehicle's wheels to roll without excessive slipping.
- **Joint Strength**: Maximum linear force for structural joints is 150000.0; maximum torque is 500000.0.
- **Anchor Strength**: Maximum linear force for cliff anchors is 200000.0; maximum torque is 800000.0.
- **Time Limit**: The task must be completed within 10,000 simulation steps (approximately 167 seconds).
""",
    
    'success_criteria': """
## Success Criteria
1. **Passage**: Vehicle reaches x >= 30.0m.
2. **Integrity**: No structural breaks (all joints must remain intact during the crossing).
3. **Smoothness**: The vehicle's vertical acceleration must remain < 30.0 m/s² (3.0g).
4. **Stability**: The vehicle's angular velocity must remain < 2.0 rad/s and net airborne rotation must not exceed 180 degrees. Stability is evaluated after simulation step 200; 5 consecutive steps with angular velocity ≥ 2.0 rad/s result in failure. The vehicle is also considered failed if it flips more than 90 degrees (tilt angle > 90°). The vehicle is considered **airborne** when its center is more than 1.5 m above the cliff top (y > 11.5 m); the 180° limit applies to rotation accumulated only while in that state.
5. **Efficiency**: Complete the traversal within the time limit.

## Design Constraints
- **Mass Budget**: < 2000 kg.
- **APIs**: Use only the primitives documented below.
""",
    
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['S_01'].values()),
}
