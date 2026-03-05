"""
E-04: Variable Mass task Prompt and Primitives definition
"""

import json
import os

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)


TASK_PROMPT = {
    "task_description": """
Design a complex structure that remains intact under sinusoidally varying mass and environmental vibration.

## Task Environment
- **Mass Variation**: Every beam's mass varies over time according to multiple frequency components.
- **Base Excitation**: The ground support oscillates vertically and horizontally (elliptical vibration).
- **Fatigue**: Joint strength (force and torque limits) decays exponentially over time.
- **Build Zone**: x in [5.0, 15.0] m, y in [1.5, 8.0] m.
- **Goal**: Maintain structural integrity until the end of the simulation.

## Task Objective
Design a structure that:
1. Spans from x=6.0m to x=14.0m.
2. Uses at least 5 beams and 6 joints.
3. Includes at least one pivot (revolute) joint.
4. Withstands the varying inertial loads and base vibration without breaking any joints.
""",
    "success_criteria": """
## Success Criteria
1. **Integrity**: All joints remain intact throughout the simulation.
2. **Span**: Structure spans from at least x <= 6.0m to x >= 14.0m.
3. **Complexity**: Meets the minimum beam (5) and joint (6) counts.
4. **Variety**: At least one joint must be a pivot (`type='pivot'`).

## Design Constraints
- **Mass Budget**: Total structure mass (instantaneous) must remain within the limit (default 400 kg).
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': '\n\n'.join(_api_data['E_04'].values()),
}
