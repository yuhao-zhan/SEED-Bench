"""
C-04: The Whisker Bot task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    APPLY_AGENT_FORCE,
    GET_AGENT_BODY,
    GET_AGENT_POSITION,
    GET_WHISKER_READINGS,
)

TASK_PROMPT = {
    "task_description": """
Design a controller for a whisker-equipped robot to navigate through a narrow, dark passage.

## Task Environment
- **Agent**: A small robot with three whisker sensors (front, left, right).
- **Passage**: A winding path with walls.
- **Goal**: Navigate from the start to the end of the passage without getting stuck.

## Task Objective
Design a control loop that:
1. Uses whisker sensor readings to detect nearby walls.
2. Applies forces to the agent to navigate the center of the path.
3. Successfully reaches the target destination at the end of the passage.
""",
    "success_criteria": """
## Success Criteria
1. **Passage Completion**: Agent reaches the end of the passage.
2. **Survival**: No sustained collisions or getting stuck.

## Design Constraints
- **APIs**: Use only the primitives documented below.
""",
    "primitives_api": API_INTRO
    + GET_AGENT_BODY
    + GET_AGENT_POSITION
    + GET_WHISKER_READINGS
    + APPLY_AGENT_FORCE,
}
