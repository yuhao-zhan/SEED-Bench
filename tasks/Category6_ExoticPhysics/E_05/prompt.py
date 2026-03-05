"""
E-05: The Magnet task Prompt and Primitives definition
"""

import json
import os

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)


TASK_PROMPT = {
    "task_description": """
Design a controller to navigate a body through a complex, invisible magnetic force field to a target zone.

## Task Environment
- **Body**: A dynamic object starting at x=8.0m, y=5.0m.
- **Force Fields**: Numerous invisible repulsive and attractive points are scattered throughout the environment.
- **Gates**: Some force fields oscillate in intensity, creating "gates" that are only passable at certain times.
- **Target Zone**: Reach the area x >= 28.0m and y in [6.0, 9.0] m.
- **Goal**: Navigate the body to the target zone by applying thrust to overcome repulsive forces and time the passage through gates.

## Task Objective
Design a control loop that:
1. Applies thrust to move the body toward the target.
2. Uses position and velocity feedback to identify and overcome repulsive "peaks" or local minima.
3. Times the approach to pass through oscillating gates when their repulsive force is weak.
4. Successfully reaches the target zone within the simulation time limit.
""",
    "success_criteria": """
## Success Criteria
1. **Target Reach**: Body reaches the target zone (x >= 28.0m, y in [6.0, 9.0]).
2. **Efficiency**: Task completed within 10,000 simulation steps.

## Design Constraints
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': '\n\n'.join(_api_data['E_05'].values()),
}
