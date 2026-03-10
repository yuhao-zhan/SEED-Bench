"""
Task-specific feedback generation for K-06: The Wiper
Grounded in environment.py, evaluator.py, and stages.py metrics.
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics for the wiper task.
    All keys are verified against evaluator.py.
    """
    task_metrics = []

    if 'cleaning_percentage' in metrics:
        task_metrics.append(f"CLEANING_PROGRESS: {metrics['cleaning_percentage']:.2f}% of particles removed from glass.")

    if 'residual_percentage' in metrics:
        task_metrics.append(f"RESIDUAL_LOAD: {metrics['residual_percentage']:.2f}% remains in target area.")

    if 'structure_mass' in metrics and 'max_structure_mass' in metrics:
        task_metrics.append(f"STRUCTURAL_MASS: {metrics['structure_mass']:.2f} kg (Limit: {metrics['max_structure_mass']:.2f} kg)")

    if 'step_count' in metrics:
        task_metrics.append(f"SIMULATION_STEPS: {metrics['step_count']}")

    return task_metrics


def get_improvement_suggestions(metrics: Dict[str, Any]) -> List[str]:
    """
    Generate diagnostic physical feedback without design spoilers.
    Uses dynamic thresholds derived from the metrics dictionary.
    """
    suggestions = []

    # 1. Mass Constraint Audit
    current_mass = metrics.get('structure_mass', 0.0)
    max_mass = metrics.get('max_structure_mass', 15.0)
    if current_mass > max_mass:
        suggestions.append("DIAGNOSTIC: Structural mass exceeds the permitted budget for this environment.")

    # 2. Coverage and Clearing Audit
    # Target: residual_percentage must be <= max_residual_percent
    res_percent = metrics.get('residual_percentage', 100.0)
    max_res = metrics.get('max_residual_percent', 20.0)
    if res_percent > max_res:
        if res_percent > 95.0:
            suggestions.append("DIAGNOSTIC: The mechanism is failing to displace particles toward the glass boundaries.")
        else:
            suggestions.append("DIAGNOSTIC: Coverage is insufficient; significant particle clumps remain in the target field.")

    # 3. Temporal/Operational Audit
    # Target: step_count must meet min_simulation_steps_required
    steps = metrics.get('step_count', 0)
    min_steps = metrics.get('min_simulation_steps_required', 480)
    if steps < min_steps and not metrics.get('success', False):
        suggestions.append("DIAGNOSTIC: Simulation terminated before the required operational duration was met.")

    # 4. Mechanical Efficiency (Generic Failure Reason)
    if metrics.get('failed') and metrics.get('failure_reason'):
        # Pass through the evaluator's specific failure reason if available
        suggestions.append(f"DIAGNOSTIC: {metrics['failure_reason']}")

    return suggestions
