"""
C-05: The Switcher task Prompt and Primitives definition
"""
from ...primitives_api import (
    API_INTRO,
    APPLY_AGENT_FORCE,
    GET_AGENT_BODY,
    GET_AGENT_POSITION,
    GET_AGENT_VELOCITY,
    GET_NEXT_REQUIRED_SWITCH,
    GET_TRIGGERED_SWITCHES,
)

TASK_PROMPT = {
    "task_description": """
Design a controller for an agent to trigger a sequence of switches in a specific order.

## Task Environment
- **Agent**: A mobile body.
- **Switches**: Several switches located throughout the environment.
- **Goal**: Trigger each switch in the required sequence.

## Task Objective
Design a control loop that:
1. Identifies the next required switch and its position.
2. Navigates the agent to the switch to trigger it.
3. Observes the set of already triggered switches.
4. Successfully completes the full sequence.
""",
    "success_criteria": """
## Success Criteria
1. **Sequence Completion**: All switches triggered in the correct order.
2. **Efficiency**: Sequence completed within the time limit.

## Design Constraints
- **APIs**: Use only the primitives documented below.
""",
    "primitives_api": API_INTRO
    + GET_AGENT_BODY
    + GET_AGENT_POSITION
    + GET_AGENT_VELOCITY
    + GET_TRIGGERED_SWITCHES
    + GET_NEXT_REQUIRED_SWITCH
    + APPLY_AGENT_FORCE,
}
