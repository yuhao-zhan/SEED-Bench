
from evaluation.feedback import Generations, Feedback
from evaluation.prompt import TASK_FEEDBACK_PROMPT, GET_IMPROVEMENT_SUGGESTIONS_PROMPT
from evaluation.utils import get_last_generation_with_code, get_llm_response

def format_task_metrics(metrics: dict) -> str:
    """
    Formats the simulation metrics into a detailed, human-readable string
    for forensic analysis. This function now includes high-resolution data
    to help diagnose failures.
    """
    
    # Core metrics
    score = metrics.get("score", 0)
    height_achieved = metrics.get("max_height_achieved", 0)
    mass = metrics.get("structure_mass", 0)
    stability = metrics.get("stability", 0.0)
    
    # Forensic and failure metrics
    structure_survived = metrics.get("structure_integrity", False)
    broken_joint_count = metrics.get("broken_joint_count", 0)
    break_step = metrics.get("joint_break_step", -1)
    break_location = metrics.get("joint_break_location")
    peak_stress = metrics.get("peak_stress_torque", 0.0)
    max_horizontal_displacement = metrics.get("max_horizontal_displacement", 0.0)
    simulation_steps = metrics.get("simulation_step_count", 0)

    # Build the feedback string
    feedback_str = f"**Overall Score:** {score:.2f}

"
    feedback_str += f"**Core Objective Metrics:**
"
    feedback_str += f"- **Max Height Achieved:** {height_achieved:.2f} units
"
    feedback_str += f"- **Total Structure Mass:** {mass:.2f} kg
"
    feedback_str += f"- **Stability Score:** {stability:.2f} (0=unstable, 1=stable)
"
    feedback_str += f"- **Max Horizontal Displacement:** {max_horizontal_displacement:.2f} units

"
    
    feedback_str += f"**Structural Integrity Analysis:**
"
    if structure_survived:
        feedback_str += "- **Result:** SUCCESS! The structure remained intact throughout the simulation.
"
    else:
        feedback_str += "- **Result:** FAILURE. The structure broke.
"

    # Forensic details for failures
    if not structure_survived:
        feedback_str += f"  - **Total Broken Joints:** {broken_joint_count}
"
        if break_step != -1:
            feedback_str += f"  - **Timeline of Failure:** First joint broke at simulation step {break_step}/{simulation_steps}.
"
        if break_location:
            feedback_str += f"  - **Location of First Failure:** Approx. (X={break_location[0]:.2f}, Y={break_location[1]:.2f})
"

    feedback_str += f"
**Mechanical Stress Analysis:**
"
    feedback_str += f"- **Peak Joint Stress (Impulse):** {peak_stress:.2f}
"
    feedback_str += "  - *Note: This value represents the maximum impulse recorded on any joint during the simulation. Higher values indicate greater stress.*
"
    
    return feedback_str.strip()


def get_feedback(generations: Generations, task_description: str) -> Feedback:
    """
    Generates feedback for the last code generation based on its execution
    metrics. This version uses the enhanced `format_task_metrics` function.
    """
    last_generation = get_last_generation_with_code(generations)
    if last_generation is None:
        return Feedback(
            feedback="No code generations to evaluate.",
            suggestions=[],
            code_with_suggestions="",
        )

    metrics = last_generation.get("metrics", {})
    
    # Format the detailed metrics using the new function
    formatted_metrics = format_task_metrics(metrics)

    # Get improvement suggestions from the LLM
    suggestions = get_improvement_suggestions(
        code=last_generation["code"],
        task_description=task_description,
        metrics=formatted_metrics,
    )
    
    # Combine everything into the final feedback
    final_feedback_prompt = TASK_FEEDBACK_PROMPT.format(
        code=last_generation["code"],
        task_description=task_description,
        metrics=formatted_metrics,
        suggestions="
".join(f"- {s}" for s in suggestions),
    )
    
    final_feedback = get_llm_response(final_feedback_prompt)

    return Feedback(
        feedback=final_feedback,
        suggestions=suggestions,
        code_with_suggestions="",  # This can be populated if needed
    )

def get_improvement_suggestions(
    code: str, task_description: str, metrics: str
) -> list[str]:
    """
    Uses an LLM to generate improvement suggestions based on the code, task,
    and the detailed metrics.
    """
    prompt = GET_IMPROVEMENT_SUGGESTIONS_PROMPT.format(
        code=code,
        task_description=task_description,
        metrics=metrics,
    )
    response = get_llm_response(prompt)
    
    # Parse the response to extract suggestions
    suggestions = [
        line.strip().lstrip("- ").rstrip(".")
        for line in response.split("
")
        if line.strip() and line.strip().startswith("-")
    ]
    
    return suggestions
