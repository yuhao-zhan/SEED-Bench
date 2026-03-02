"""
Task-specific feedback for F-04: The Filter (Three-way)
Diagnostic metrics only; no zone coordinates or aperture hints. Agent must infer from patterns.
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    metric_parts = []

    total = metrics.get("initial_particle_count", 0)
    if total:
        metric_parts.append(f"**Total particles**: {total}")

    small_in_small = metrics.get("small_in_small_zone", 0)
    medium_in_medium = metrics.get("medium_in_medium_zone", 0)
    large_in_large = metrics.get("large_in_large_zone", 0)
    correct = small_in_small + medium_in_medium + large_in_large

    metric_parts.append(f"**Correctly placed** (type matches region): {correct} / {total}")
    metric_parts.append(f"  - Type-S in lower region: {small_in_small}")
    metric_parts.append(f"  - Type-M in middle region: {medium_in_medium}")
    metric_parts.append(f"  - Type-L in upper region: {large_in_large}")

    purity = metrics.get("purity_percent", 0)
    target = metrics.get("min_purity_percent", 36)
    metric_parts.append(f"**Purity**: {purity:.1f}% (target: {target:.0f}%)")

    if metrics.get("contaminated", False):
        metric_parts.append("**Cross-region** (type in wrong region):")
        if metrics.get("large_in_small_zone", 0) > 0:
            metric_parts.append(f"  - Type-L in lower: {metrics['large_in_small_zone']}")
        if metrics.get("small_in_large_zone", 0) > 0:
            metric_parts.append(f"  - Type-S in upper: {metrics['small_in_large_zone']}")
        if metrics.get("medium_in_small_zone", 0) > 0:
            metric_parts.append(f"  - Type-M in lower: {metrics['medium_in_small_zone']}")
        if metrics.get("medium_in_large_zone", 0) > 0:
            metric_parts.append(f"  - Type-M in upper: {metrics['medium_in_large_zone']}")

    if "small_above_sieve" in metrics or "large_below_sieve" in metrics:
        metric_parts.append("**Spatial distribution** (for diagnosis):")
        if "small_above_sieve" in metrics:
            metric_parts.append(f"  - Type-S still above separator: {metrics['small_above_sieve']}")
        if "large_below_sieve" in metrics:
            metric_parts.append(f"  - Type-L fell through separator: {metrics['large_below_sieve']}")

    if "structure_mass" in metrics:
        metric_parts.append(f"**Structure mass**: {metrics['structure_mass']:.2f} kg (limit: {metrics.get('max_structure_mass', 75):.0f} kg)")
    if "structure_broken" in metrics:
        metric_parts.append(f"**Structure**: {'BROKEN' if metrics['structure_broken'] else 'intact'}")
    if "beam_count" in metrics:
        metric_parts.append(f"**Beams used**: {metrics['beam_count']} (max: {metrics.get('max_beams', 6)})")

    return metric_parts


def get_improvement_suggestions(
    metrics: Dict[str, Any], score: float, success: bool, failed: bool,
    failure_reason: str = None, error: str = None,
) -> List[str]:
    suggestions = []
    if error:
        if "exceeds" in error.lower() and "mass" in error.lower():
            suggestions.append("- Reduce structure mass")
        elif "exceeds" in error.lower() and "beams" in error.lower():
            suggestions.append("- Use fewer beams")
        elif "build zone" in error.lower():
            suggestions.append("- Place beams within the build zone")
    elif failed and failure_reason:
        if "design constraint" in failure_reason.lower():
            suggestions.append("- Check mass and beam limits")
        elif "purity" in failure_reason.lower():
            suggestions.append("- Use distribution metrics to infer which separator settings need adjustment")
        elif "structure" in failure_reason.lower():
            suggestions.append("- Strengthen or simplify the structure")
    return suggestions
