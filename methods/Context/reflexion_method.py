"""
Reflexion method integration for DaVinciBench evaluation framework.

Implements the Reflexion approach: a separate reflection LLM analyzes failed
attempts and produces diagnostic reflections; the main solver receives these
reflections when generating the next revision.

Flow per iteration (after a failure):
  1. Reflection LLM: (task, failed code, feedback) → diagnostic reflection text
  2. Reflections are accumulated (FIFO, max 3) and injected into revision prompts
  3. Solver generates next attempt using revision prompt + reflections

The reflection LLM is a separate SolverInterface (API-only, e.g. deepseek-v3.2);
the main solver is the agent under test.

Reference:
  Reflexion: Language Agents with Verbal Reinforcement Learning
  https://arxiv.org/abs/2303.11366
  DaVinciBench/baseline/Context/reflexion/
"""

from typing import List, Any

# Revision demonstration block used in revision prompts (shared with evaluation.prompt)
from evaluation.prompt import REVISION_DEMONSTRATION


# --------------------------------------------------------------------------- #
# Reflection LLM system prompt and header
# --------------------------------------------------------------------------- #
# Design adapted from DaVinciBench/baseline/Context/reflexion (REFLECT_INSTRUCTION
# and REFLECTION_HEADER in hotpotqa_runs/prompts.py), with wording adapted for
# physics design (task/code/feedback).

REFLEXION_SYSTEM_PROMPT = (
    "You are an advanced reasoning agent that can improve based on self-reflection. "
    "You specialize in analyzing failed attempts at designing physical systems in 2D physics simulations.\n\n"
    "When given a previous design attempt and its evaluation feedback (metrics, scores, errors), "
    "you must:\n"
    "1. Diagnose the likely physical reason for failure or underperformance\n"
    "2. Devise a new, concise, high-level plan that aims to avoid the same failure\n\n"
    "Be specific and actionable. Focus on the physics (forces, geometry, stability, constraints), "
    "not code syntax. Use complete sentences. Keep your reflection to 3-8 sentences."
)

REFLEXION_HEADER = (
    "You have attempted this task before and the attempt(s) were unsuccessful. "
    "The following reflection(s) provide diagnostic analysis and high-level plans "
    "to avoid repeating the same failures. Use them to improve your strategy.\n\n"
)


# --------------------------------------------------------------------------- #
# Reflection prompt (sent to the reflection LLM)
# --------------------------------------------------------------------------- #

def format_reflection_prompt(
    task_prompt: dict,
    previous_code: str,
    feedback: str,
    iteration: int,
) -> str:
    """
    Format the prompt sent to the reflection LLM after a failed iteration.
    The reflection LLM reads the task, the failed code, and the baseline feedback,
    then produces a diagnostic reflection.

    Args:
        task_prompt: Dict with task_description, success_criteria, primitives_api
        previous_code: The code that was attempted and failed
        feedback: Baseline feedback string (metrics, scores, errors - no suggestions)
        iteration: The iteration number that just failed
    Returns:
        Formatted reflection prompt string.
    """
    return f"""# Task Description

{task_prompt['task_description']}

# Success Criteria

{task_prompt['success_criteria']}

# Previous Attempt (Iteration {iteration})

```python
{previous_code}
```

# Evaluation Feedback

{feedback}

# Your Task

The above attempt was unsuccessful. In a few sentences:

1. **Diagnose**: What is the likely physical reason for failure? (e.g., insufficient force, wrong geometry, instability, constraint violation, energy loss, timing issue, wrong dimensions, etc.)

2. **Plan**: Devise a new, concise, high-level plan that aims to avoid the same failure in the next attempt. Be specific about what physical parameters or design choices should change and why.

Reflection:"""


# --------------------------------------------------------------------------- #
# Format accumulated reflections for injection into revision prompt
# --------------------------------------------------------------------------- #

def format_reflections_str(reflections: List[str]) -> str:
    """
    Format accumulated reflections into a string for prompt injection.

    Args:
        reflections: List of reflection strings
    Returns:
        Formatted reflections string (empty if no reflections)
    """
    if not reflections:
        return ''
    return REFLEXION_HEADER + 'Reflections:\n- ' + '\n- '.join(
        [r.strip() for r in reflections]
    )


# Backward compatibility: same function under old name
_format_reflections_str = format_reflections_str


# --------------------------------------------------------------------------- #
# Revision prompts with reflections (for the main solver)
# --------------------------------------------------------------------------- #

def format_revision_prompt_reflexion(
    task_prompt: dict,
    reflections_str: str,
    best_code: str,
    best_feedback: str,
    previous_code: str,
    previous_feedback: str,
    current_feedback: str,
    best_iteration: int = None,
    previous_iteration: int = None,
    current_iteration: int = None,
) -> str:
    """
    Format revision prompt for reflexion method.
    Like format_revision_prompt_best_plus_previous but with reflections injected.

    Args:
        task_prompt: Dict from load_task_prompt
        reflections_str: Formatted reflections string from format_reflections_str()
        best_code: Code from the best-scoring iteration
        best_feedback: Feedback from the best-scoring iteration
        previous_code: Code from the previous iteration
        previous_feedback: Feedback from the previous iteration
        current_feedback: Feedback from the most recent iteration
        best_iteration: Iteration number of the best score
        previous_iteration: Iteration number of the previous attempt
        current_iteration: Current iteration number
    Returns:
        Formatted revision prompt string.
    """
    show_previous = previous_code and (
        best_iteration != previous_iteration
        if best_iteration is not None and previous_iteration is not None
        else True
    )

    return f"""# Task Description

{task_prompt['task_description']}

# Success Criteria

{task_prompt['success_criteria']}

# Available Primitives API

{task_prompt['primitives_api']}

{REVISION_DEMONSTRATION}

# Best-Scoring Attempt (Reference)

```python
{best_code}
```

Feedback: {best_feedback}
{'' if not show_previous else f'''
# Previous Attempt

```python
{previous_code}
```

Feedback: {previous_feedback}
'''}

# Reflections from Previous Attempts

{reflections_str}

# Your Task: Diagnose and Fix

Use the reflections above to guide your next attempt. They contain diagnostic analysis of why previous attempts failed and high-level plans for improvement.

Compare these attempts and reflections. Learn from what worked best and what the reflections recommend. Provide an improved solution.

## Step 1: Physical Diagnosis (Required)

Based on the reflections and feedback, what is the most important physical issue to address?

## Step 2: Implement the Fix

**Code Requirements**:
- All code must be inside functions
- Do not use `sandbox` variable outside functions
- Provide COMPLETE code

**Output Format**:

```python
def build_agent(sandbox):
    # Your improved implementation
    return chassis

def agent_action(sandbox, agent_body, step_count):
    # Control logic if needed
    pass
```

Begin with your analysis, then provide the code.
"""


def format_revision_prompt_reflexion_simple(
    task_prompt: dict,
    reflections_str: str,
    previous_code: str,
    feedback: str,
) -> str:
    """
    Simplified reflexion revision prompt when there is no best-scoring attempt yet
    (e.g., iteration 2 where only one attempt has been made).

    Args:
        task_prompt: Dict from load_task_prompt
        reflections_str: Formatted reflections string
        previous_code: Code from the previous iteration
        feedback: Feedback from the previous iteration
    Returns:
        Formatted revision prompt string.
    """
    return f"""# Task Description

{task_prompt['task_description']}

# Success Criteria

{task_prompt['success_criteria']}

# Available Primitives API

{task_prompt['primitives_api']}

{REVISION_DEMONSTRATION}

# Reflections from Previous Attempts

{reflections_str}

# Previous Iteration Code

```python
{previous_code}
```

# Evaluation Feedback

{feedback}

# Your Task: Diagnose and Fix

Use the reflections above to guide your next attempt. They contain diagnostic analysis of why previous attempts failed and high-level plans for improvement.

## Step 1: Physical Diagnosis (Required)

Based on the reflections and feedback, what is the most important physical issue to address?

## Step 2: Implement the Fix

**Code Requirements**:
- All code must be inside functions
- Do not use `sandbox` variable outside functions
- Provide COMPLETE code

**Output Format**:

```python
def build_agent(sandbox):
    # Your improved implementation
    return chassis

def agent_action(sandbox, agent_body, step_count):
    # Control logic if needed
    pass
```

Begin with your analysis, then provide the code.
"""
