import re
from stages import _replace_weld_constraint_line

# Current prompt line
line = "- **Constraint**: Beam-to-beam welds break when reaction force **reaches or exceeds** 50000 N for 3 consecutive simulation steps."
# Example: 40000 N and 2 steps
# Should result in: - **Constraint**: Beam-to-beam welds break when reaction force **reaches or exceeds** 40000 N (originally 50000 N in the source environment) for 2 consecutive simulation steps (originally 3 consecutive simulation steps in the source environment)."

result = _replace_weld_constraint_line(
    line,
    target_force=40000.0,
    base_force=50000.0,
    target_steps=2,
    base_steps=3
)

print(f"Original: {line}")
print(f"New:      {result}")

# Validate if it matches the expected structure:
# Replaces 50000 N -> 40000 N (originally 50000 N in the source environment)
# Replaces 3 consecutive simulation steps -> 2 consecutive simulation steps (originally 3 consecutive simulation steps in the source environment)
