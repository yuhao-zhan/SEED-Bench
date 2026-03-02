"""
Self-Refine method integration for DaVinciBench evaluation framework.

Implements the Self-Refine paper approach (Madaan et al., 2023) where the
SAME solver model acts as both critic and coder. Pipeline matches the
original repository (baseline/Context/self-refine):

  - Within each round: NO system verifier. The model only self-evaluates
    (critique) and refines until the model says "It is correct."
  - After the model stops self-refining: run the system verifier ONCE to get
    baseline-style feedback for the next round.

Prompt wording is taken directly from the original repo:
  - GSM feedback instruction (src/gsm/feedback.py): "There is an error in the
    code above because of lack of understanding of the question. What is the
    error? ..." → adapted for "task" and add stopping phrase.
  - PIE iterate pattern (src/pie/task_iterate.py): code + instruction + feedback
    + "Improved version:" / "Okay, let's use this feedback to improve the code."

Reference:
  Self-Refine: Iterative Refinement with Self-Feedback
  https://arxiv.org/abs/2303.17651
  Original repo: baseline/Context/self-refine (GSM, PIE)
"""

# --------------------------------------------------------------------------- #
# Self-feedback (self-verify) prompt — from original repo + strict output rule
# --------------------------------------------------------------------------- #
# GSM (src/gsm/feedback.py) instruction (exact):
#   "# There is an error in the code above because of lack of understanding of the question. What is the error? ..."
# Stopping (GSM run.py): "it is correct" in feedback.lower()
# We require the model to output exactly this phrase when correct, so we can detect it reliably.

SELF_VERIFY_INSTRUCTION = (
    "# Review the code above for the task. Go through semantically complete blocks and check if everything looks good.\n"
    "# You must choose exactly ONE of the following — never both:\n"
    "#\n"
    "# (A) If there ARE errors or the code does not correctly solve the task:\n"
    "#     Explain what is wrong and what to fix. Do NOT write \"It is correct.\" in this case.\n"
    "#     Writing \"It is correct.\" means the code needs no changes; so if you suggest any fix or provide any corrected code, you must NOT say \"It is correct.\"\n"
    "#\n"
    "# (B) If there are NO errors and the code correctly solves the task:\n"
    "#     You MUST end your response with exactly this sentence, and nothing else after it:\n"
    "#     \"It is correct.\"\n"
    "#     Do not add any explanation, code, or fixes after it. We use this exact phrase to stop refinement.\n"
    "#\n"
    "# Rule: If you list any errors, suggest any changes, or provide any improved/corrected code, then you are in case (A) — never append \"It is correct.\"."
)


def format_self_feedback_prompt(code: str, task_prompt: dict) -> str:
    """
    Build the prompt for the solver to critique its own code (self-verify).
    Does NOT include any system/verifier feedback — only task and code.
    Matches original Self-Refine: model sees only its output and task.

    Args:
        code:        Current code solution.
        task_prompt: Task prompt dict with task_description, success_criteria, etc.

    Returns:
        Formatted prompt string.
    """
    task_description = task_prompt.get("task_description", "")
    success_criteria = task_prompt.get("success_criteria", "")
    return f"""## Task Description

{task_description}

## Success Criteria

{success_criteria}

## Your Current Code

```python
{code}
```

{SELF_VERIFY_INSTRUCTION}
"""


# Required phrase when code is correct (prompt instructs model to output this exactly).
REQUIRED_CORRECT_PHRASE = "it is correct"


def self_verify_response_contradictory(model_output: str) -> bool:
    """
    True if the model said "It is correct." but also suggested fixes (e.g. provided
    corrected code). In that case we do not treat as stop — the model violated the
    instruction (choose A or B, not both). Does not weaken the phrase when used correctly.
    """
    if not model_output or not isinstance(model_output, str):
        return False
    lower = model_output.lower()
    if REQUIRED_CORRECT_PHRASE not in lower:
        return False
    # Signs that the model also suggested a fix: code block with build_agent, or fix wording
    if "def build_agent" in model_output:
        return True
    fix_phrases = (
        "corrected code", "here's the fix", "improved version", "here is the corrected",
        "fixed code", "corrected implementation", "the following code", "```python",
    )
    return any(p in lower for p in fix_phrases)


def self_verify_says_correct(model_output: str) -> bool:
    """
    True if the model's self-verify output indicates no more refinement needed.
    The prompt requires the model to end with "It is correct." when the code is correct.
    We ignore "It is correct." when the same response also suggests fixes (contradiction).
    """
    if not model_output or not isinstance(model_output, str):
        return False
    if REQUIRED_CORRECT_PHRASE not in model_output.lower():
        return False
    if self_verify_response_contradictory(model_output):
        return False  # Model said "correct" but also gave fixes — treat as needing refinement
    return True


# --------------------------------------------------------------------------- #
# Refinement prompt for INNER loop (no system feedback)
# --------------------------------------------------------------------------- #
# From PIE task_iterate (src/pie/task_iterate.py): template is
#   {slow_code} + {instr} + {feedback} + "# Improved version:"
# From acronym/responsegen: "Okay, let's use this feedback to improve the ..."
# Inner loop uses only self_feedback (model's own critique), no verifier output.

SELF_REFINE_INNER_REVISION_TEMPLATE = """# Task Description

{task_description}

# Success Criteria

{success_criteria}

# Available Primitives API

{primitives_api}

# Previous Code

```python
{previous_code}
```

# Your Self-Analysis (what is wrong or how to improve)

{self_feedback}

# Improved version

Okay, let's use this feedback to improve the code. Provide the complete improved Python code.
"""


def format_revision_prompt_self_refine_inner(
    task_prompt: dict,
    previous_code: str,
    self_feedback: str,
) -> str:
    """
    Build the refinement prompt for the inner self-refine loop.
    Uses only the model's self_feedback (no system verifier feedback).
    """
    return SELF_REFINE_INNER_REVISION_TEMPLATE.format(
        task_description=task_prompt.get("task_description", ""),
        success_criteria=task_prompt.get("success_criteria", ""),
        primitives_api=task_prompt.get("primitives_api", ""),
        previous_code=previous_code,
        self_feedback=self_feedback,
    )


# --------------------------------------------------------------------------- #
# Refinement prompt when system feedback is available (e.g. for next round)
# --------------------------------------------------------------------------- #
# Used only when we want to pass system feedback into the prompt; the main
# inner loop uses format_revision_prompt_self_refine_inner (no system feedback).
# Kept for compatibility if needed elsewhere.

SELF_REFINE_REVISION_TEMPLATE_WITH_SYSTEM_FB = """# Task Description

{task_description}

# Success Criteria

{success_criteria}

# Available Primitives API

{primitives_api}

# Previous Iteration Code

```python
{previous_code}
```

# Evaluation Feedback (from system verifier)

{feedback}

# Your Self-Analysis (if any)

{self_feedback}

# Your Task: Implement the Fix

Implement the improved code based on the feedback above.
Provide COMPLETE code defining `build_agent(sandbox)` and optionally `agent_action(sandbox, agent_body, step_count)`.
"""


def format_revision_prompt_self_refine(
    task_prompt: dict,
    previous_code: str,
    feedback: str,
    self_feedback: str,
) -> str:
    """
    Build the refinement prompt when both system feedback and self-feedback exist.
    (Used for optional contexts; inner loop uses format_revision_prompt_self_refine_inner.)
    """
    return SELF_REFINE_REVISION_TEMPLATE_WITH_SYSTEM_FB.format(
        task_description=task_prompt.get("task_description", ""),
        success_criteria=task_prompt.get("success_criteria", ""),
        primitives_api=task_prompt.get("primitives_api", ""),
        previous_code=previous_code,
        feedback=feedback,
        self_feedback=self_feedback or "(No self-analysis yet.)",
    )


# Legacy suffix (kept for any existing callers).
def build_self_refine_suffix(self_feedback: str) -> str:
    return f"\n\n## Your Self-Analysis\n\n{self_feedback}\n\n## Refine\n\nOkay, let's use this feedback to improve the code."
