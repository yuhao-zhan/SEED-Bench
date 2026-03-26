"""
F-03: The Excavator task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'F_03' in _api_data and 'API_INTRO' in _api_data['F_03']:
    del _api_data['F_03']['API_INTRO']


TASK_PROMPT = {
    "task_description": """
Design an excavator arm and scoop to move granular material over an obstacle.

## Task Environment
- **Material**: 200 sand particles in a pit with x=[0.0, 5.0] m and y=[0.0, 2.5] m.
- **Particle Properties**: Each particle has a radius of 0.06 m and a material density of 1500.0 kg/m³.
- **Obstacle**: A central wall at x=-1.0 m (y=[0.5, 1.5] m, width=0.24 m). Use `has_central_wall()` to check environment state.
- **Target Hopper**: Located at x=-5.0 m, y=3.0 m. Particles count as deposited if their center lies in the hopper zone x=[-6.0, -4.0] m, y=[0.5, 5.0] m.
- **Build Zone**: Mechanism must be built in x=[-4.0, 2.0], y=[0.0, 5.0]. Base is anchored at x=-2.0 m, y=0.0 m (evaluator accepts any body within 0.5 m of this position).
- **Time Limit**: Complete the task within 40 seconds.

## Task Objective
Design a mechanism that:
1. Scoops up granular material from the pit (x > 0).
2. Lifts and moves the material over the central wall (x = -1.0).
3. Deposits the material into the target hopper at x=-5.0.

## Design Constraints
- **Mass Budget**: Total structure mass <= 800 kg.
- **Beam Dimensions**: Each beam width and height must be between 0.1 m and 1.5 m. Default densities: Beam=300.0, Anchored Base=400.0, Bucket/Scoop=280.0 kg/m³.
- **Motor Torque**: Maximum motor torque for revolute joints is 100.0 N·m.
- **Joint Strength**: Joints are unbreakable in the source environment (reaction force and torque limits are effectively infinite).
- **Per-scoop capacity**: Maximum particles carried per scoop per trip: 999 in the source environment (effectively unlimited).
- **Scoop Mechanics**: To facilitate transport, a scoop (created via `add_scoop`) will automatically capture and "carry" particles within a 2.0 m margin of its structure when not tilted beyond 0.6 radians (~34°). Captured particles are released ONLY when the scoop is over the target hopper and its rotation angle exceeds 0.6 radians.
- **Kinematic Requirement**: The mechanism must have at least 2 degrees of freedom (Arm + Bucket), i.e. at least 2 revolute joints.
- **APIs**: Use only the primitives documented below.
""",
    "success_criteria": """
1. **Material Transfer**: At least 15 sand particles are deposited in the hopper zone (x=[-6.0, -4.0] m, y=[0.5, 5.0] m; center at x=-5.0, y=3.0).

2. **Integrity**: Mechanism remains intact throughout the operation.
""",
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['F_03'].values()),
}
