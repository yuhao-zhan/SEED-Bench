import re
import math

# Simulate mass string formatter
def _mass_str(m: float) -> str:
    return f"{m:.0f}" if m == int(m) else f"{m:.1f}"

# Mock base description from prompt.py
base_desc = """
- **Mass Budget**: Total structure mass must be less than 100 kg.
"""

target_max_mass = 2.8
base_max_mass = 100.0

mass_desc_pattern = re.compile(
    r"(- \*\*Mass Budget\*\*: Total structure mass must be less than )(\d+\.?\d*) kg\."
)

new_desc = mass_desc_pattern.sub(
    lambda m: f"{m.group(1)}{_mass_str(target_max_mass)} kg (originally {_mass_str(base_max_mass)} kg in the source environment).",
    base_desc,
)

print(f"Old: {base_desc}")
print(f"New: {new_desc}")

# Mock base success criteria from prompt.py
base_criteria = """
- **Mass Budget**: < 100 kg.
"""
mass_pattern = re.compile(r"(- \*\*Mass Budget\*\*: < )(\d+\.?\d*) kg\.")
new_criteria = mass_pattern.sub(
    lambda m: f"{m.group(1)}{_mass_str(target_max_mass)} kg (originally {_mass_str(base_max_mass)} kg in the source environment).",
    base_criteria,
)
print(f"Old Criteria: {base_criteria}")
print(f"New Criteria: {new_criteria}")
