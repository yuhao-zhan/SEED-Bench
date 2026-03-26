import re

prompt = """
- **Goal**: Reach x >= 0.1m beyond the edge.
"""
criteria = """
(Tip reaches x >= 0.1m).
"""

target_overhang = 0.8
base_overhang = 0.1

pattern_prompt = r"(\s*-\s*\*\*Goal\*\*: Reach x >= )(\d+\.?\d*)m( beyond the edge\.?)"
new_prompt = re.sub(pattern_prompt, f"\\g<1>{target_overhang:.2f}m (originally {base_overhang:.2f}m in the source environment)\\g<3>", prompt)
print(f"Prompt: {new_prompt}")

pattern_criteria = r"(\(Tip reaches x >= )(\d+\.?\d*)(m\)\.)"
new_criteria = re.sub(pattern_criteria, f"\\g<1>{target_overhang:.2f}m (originally {base_overhang:.2f}m in the source environment)).", criteria)
print(f"Criteria: {new_criteria}")

