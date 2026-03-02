"""
TextGrad method integration for DaVinciBench evaluation framework.

Implements Design A: The TextGrad engine (default deepseek-v3.2) handles both
gradient computation and optimization. The solver is only used for the initial
code generation (iteration 1). After that, TextGrad manages code improvement.

Flow per iteration (iter >= 2):
  1. Gradient computation (LLM backward pass): analyze code + deterministic feedback -> textual gradient
  2. Optimizer step (LLM): code + gradient -> improved code
  3. Deterministic verification: run code, get metrics/score/feedback

References:
  - TextGrad paper: https://arxiv.org/abs/2406.04996
  - TextGrad repo: DaVinciBench/baseline/Context/textgrad/
"""
import os
import sys
import re
import logging

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Path setup: locate the TextGrad library from the baseline repository
# --------------------------------------------------------------------------- #
# methods/Context -> methods -> scripts -> 2D_exploration -> DaVinciBench
_CONTEXT_DIR = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS_DIR = os.path.dirname(os.path.dirname(_CONTEXT_DIR))
_DAVINCI_ROOT = os.path.normpath(os.path.join(_SCRIPTS_DIR, '..', '..'))
_TEXTGRAD_LIB = os.path.join(_DAVINCI_ROOT, 'baseline', 'Context', 'textgrad')

_textgrad_imported = False


def _ensure_textgrad_importable():
    """Add the TextGrad library to sys.path so we can ``import textgrad``."""
    global _textgrad_imported
    if _textgrad_imported:
        return
    # Disable TextGrad's file logging to scripts/logs; all data is saved in evaluation_results JSON.
    if "TEXTGRAD_DISABLE_LOGGING" not in os.environ:
        os.environ["TEXTGRAD_DISABLE_LOGGING"] = "1"
    if not os.path.isdir(_TEXTGRAD_LIB):
        raise ImportError(
            f"TextGrad library not found at {_TEXTGRAD_LIB}. "
            "Make sure the baseline repository is present at "
            "DaVinciBench/baseline/Context/textgrad/"
        )
    if _TEXTGRAD_LIB not in sys.path:
        sys.path.insert(0, _TEXTGRAD_LIB)
    _textgrad_imported = True


# --------------------------------------------------------------------------- #
# Engine creation
# --------------------------------------------------------------------------- #

def create_textgrad_engine(engine_name: str = 'deepseek-v3.2'):
    """
    Create a TextGrad engine for gradient computation and optimization.

    Uses the same API gateway (key + base_url) as ``SolverInterface`` so that
    no extra environment variables are needed.
    """
    _ensure_textgrad_importable()

    # Import the shared API credentials from the solver (evaluation package)
    from evaluation.solver_interface import SolverInterface
    api_key = SolverInterface.API_KEY
    base_url = SolverInterface.BASE_URL

    from openai import OpenAI
    from textgrad.engine.local_model_openai_api import ChatExternalClient

    client = OpenAI(api_key=api_key, base_url=base_url)
    engine = ChatExternalClient(client=client, model_string=engine_name)
    return engine


# --------------------------------------------------------------------------- #
# Gradient computation (backward pass)
# --------------------------------------------------------------------------- #

GRADIENT_SYSTEM_PROMPT = (
    "You are a critical code analyst for a physics simulation optimization system. "
    "Your job is to analyze code solutions and their execution results, then provide "
    "specific, actionable feedback about what went wrong and how to improve. "
    "Focus on identifying bugs, logic errors, physics misconceptions, and missing "
    "implementation details. Be concrete and precise in your analysis."
)


def compute_gradient(engine, code: str, feedback: str, task_prompt: dict) -> str:
    """
    Backward pass: an LLM analyzes the code + deterministic verifier feedback
    and generates structured textual gradients (improvement directions).

    Args:
        engine:      TextGrad engine for the backward pass.
        code:        Current code solution.
        feedback:    Deterministic feedback from the verifier (metrics / score / errors).
        task_prompt: Task prompt dict (task_description, success_criteria, primitives_api).

    Returns:
        Textual gradient string.
    """
    task_desc = task_prompt.get('task_description', '')
    success_criteria = task_prompt.get('success_criteria', '')

    backward_prompt = (
        f"Analyze the following Python code solution for a 2D physics simulation task.\n\n"
        f"## Task Description\n{task_desc}\n\n"
        f"## Success Criteria\n{success_criteria}\n\n"
        f"## Current Code\n```python\n{code}\n```\n\n"
        f"## Execution Results and Metrics\n{feedback}\n\n"
        f"## Your Analysis\n"
        f"Provide a detailed, structured analysis:\n"
        f"1. **Bugs and Errors**: Identify syntax errors, runtime errors, or logic bugs.\n"
        f"2. **Physics / Strategy Issues**: Is the physical approach correct for this task?\n"
        f"3. **Implementation Gaps**: What is missing or incorrectly implemented?\n"
        f"4. **Specific Improvements**: List concrete, actionable changes that would "
        f"improve the code's score towards 100/100.\n\n"
        f"Be specific about line-level issues and give clear improvement directions."
    )

    try:
        gradient_text = engine.generate(backward_prompt, system_prompt=GRADIENT_SYSTEM_PROMPT)
        return gradient_text
    except Exception as e:
        logger.error(f"Gradient computation failed: {e}")
        return (
            f"(Gradient computation failed, falling back to raw feedback)\n\n"
            f"Execution feedback:\n{feedback}"
        )


# --------------------------------------------------------------------------- #
# TextGrad Variable / Optimizer helpers
# --------------------------------------------------------------------------- #

CODE_ROLE_DESCRIPTION = (
    "Complete Python code solution for a 2D physics simulation task. "
    "The code defines a build_agent(sandbox) function that uses physics primitives "
    "(create_box, create_ball, create_polygon, create_segment, create_joint, "
    "apply_force, etc.) to construct objects and achieve the task goal. "
    "May also define agent_action(sandbox, agent_body, step_count) for active control."
)

CODE_CONSTRAINTS = [
    "The output MUST be a complete, valid Python program.",
    "The code MUST define a `build_agent(sandbox)` function that creates physics "
    "objects and returns the main body.",
    "The code MAY optionally define an `agent_action(sandbox, agent_body, step_count)` "
    "function for active control.",
    "Use ONLY the provided physics simulation primitives API.",
    "Output ONLY the improved Python code. Do NOT include markdown formatting, "
    "code fences (```), or explanations outside the code.",
]


def init_textgrad_components(code: str, engine):
    """
    Create the TextGrad Variable and Optimizer after the first iteration.

    Args:
        code:   The initial code produced by the solver (iteration 1).
        engine: TextGrad engine used by the optimizer.

    Returns:
        ``(code_var, optimizer)`` tuple.
    """
    _ensure_textgrad_importable()
    import textgrad as tg
    from textgrad.optimizer import TextualGradientDescent

    code_var = tg.Variable(
        code,
        requires_grad=True,
        role_description=CODE_ROLE_DESCRIPTION,
    )

    optimizer = TextualGradientDescent(
        engine=engine,
        parameters=[code_var],
        constraints=CODE_CONSTRAINTS,
        gradient_memory=3,        # remember last 3 gradients for momentum-like context
    )

    return code_var, optimizer


# --------------------------------------------------------------------------- #
# Full optimisation step
# --------------------------------------------------------------------------- #

def textgrad_optimize_step(code_var, optimizer, engine, feedback: str, task_prompt: dict):
    """
    Execute one TextGrad optimisation step (2 LLM calls):

    1. **Gradient** (backward): LLM analyses code + deterministic feedback.
    2. **Optimizer**: LLM generates improved code from code + gradients.

    Args:
        code_var:   ``textgrad.Variable`` holding the current code.
        optimizer:  ``TextualGradientDescent`` instance.
        engine:     TextGrad engine for gradient computation.
        feedback:   Deterministic verifier feedback string.
        task_prompt: Task prompt dict.

    Returns:
        ``(new_code, raw_output_info, gradient_text)``
        *new_code* is ``None`` on failure (raw_output_info contains the error message).
    """
    _ensure_textgrad_importable()
    import textgrad as tg

    previous_code = code_var.value          # save for rollback

    # 1. Zero gradients
    optimizer.zero_grad()

    # 2. Compute gradient (backward pass – 1 LLM call)
    gradient_text = compute_gradient(engine, code_var.value, feedback, task_prompt)

    # 3. Attach gradient to the Variable
    gradient_var = tg.Variable(
        gradient_text,
        requires_grad=False,
        role_description="textual gradient: analysis of code issues and improvement suggestions",
    )
    code_var.gradients.add(gradient_var)
    code_var.gradients_context[gradient_var] = {
        "context": (
            f"The code was written to solve a 2D physics simulation task.\n\n"
            f"Code:\n{code_var.value}\n\n"
            f"Execution and scoring feedback:\n{feedback}"
        ),
        "response_desc": "execution feedback and scoring metrics for the code solution",
        "variable_desc": code_var.get_role_description(),
    }

    # 4. Optimizer step -- manual execution to capture raw LLM response
    #    (replaces optimizer.step() to expose the raw optimizer output)
    try:
        opt_prompt = optimizer._update_prompt(code_var)
        raw_optimizer_response = engine(opt_prompt, system_prompt=optimizer.optimizer_system_prompt)
        logger.info("TextGrad optimizer raw response captured (%d chars)", len(raw_optimizer_response) if raw_optimizer_response else 0)
        try:
            new_value = raw_optimizer_response.split(optimizer.new_variable_tags[0])[1].split(optimizer.new_variable_tags[1])[0].strip()
        except (IndexError, AttributeError) as tag_err:
            logger.error(f"TextGrad optimizer: tag extraction failed: {tag_err}")
            code_var.set_value(previous_code)
            return None, f"TextGrad optimizer tag extraction failed.\nRaw response:\n{raw_optimizer_response}", gradient_text
        code_var.set_value(new_value)
        if getattr(optimizer, 'do_gradient_memory', False):
            optimizer.update_gradient_memory(code_var)
        new_code = code_var.value
        return new_code, raw_optimizer_response, gradient_text
    except Exception as e:
        logger.error(f"TextGrad optimizer step error: {e}")
        code_var.set_value(previous_code)
        return None, f"TextGrad optimizer error: {e}", gradient_text


# --------------------------------------------------------------------------- #
# Code extraction / clean-up
# --------------------------------------------------------------------------- #

def extract_code_from_textgrad_output(text: str):
    """
    Extract valid Python code from the TextGrad optimizer output.

    The optimizer is instructed to output raw code, but it may still include
    markdown fences or extra commentary.  This function tries multiple
    strategies and returns the best match, or ``None`` on failure.
    """
    if not text:
        return None

    # Strategy 1: extract from markdown code blocks
    code_block_pattern = r'```(?:python)?\s*\n(.*?)```'
    matches = re.findall(code_block_pattern, text, re.DOTALL)
    if matches:
        code = max(matches, key=len).strip()
        if 'def build_agent' in code:
            return code

    # Strategy 2: the whole text is already code
    if 'def build_agent' in text:
        lines = text.split('\n')
        code_start = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(('import ', 'from ', 'def ', '#', '"""', "'''")):
                code_start = i
                break
        if code_start is not None:
            return '\n'.join(lines[code_start:]).strip()
        return text.strip()

    # Strategy 3: return raw text (caller will validate)
    return text.strip() if text.strip() else None
