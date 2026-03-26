import re

def update_task_description_for_visible_changes(description, target_y, base_y):
    # Update "at least y=9.0m"
    pattern = r"(at least y=)(\d+\.?\d*)m( \(originally y=[\d.]+m in the source environment\))?"
    description = re.sub(pattern, f"\g<1>{target_y:.1f}m (originally y={base_y:.1f}m in the source environment)", description)
    # Update "Object center reaches y >= 9.0m" (constraints section)
    pattern_y_ge = r"(reaches y >= )(\d+\.?\d*)m( \(originally y >= [\d.]+m in the source environment\))?"
    description = re.sub(pattern_y_ge, f"\g<1>{target_y:.1f}m (originally y >= {base_y:.1f}m in the source environment)", description)
    return description

desc = """Design a scissor lift mechanism that can lift objects vertically using motor rotation or linear forces.
- **Target Height**: Lift the object so its center reaches at least y=9.0m.
- **Constraints**: Object center reaches y >= 9.0m."""

print(update_task_description_for_visible_changes(desc, 10.5, 9.0))
