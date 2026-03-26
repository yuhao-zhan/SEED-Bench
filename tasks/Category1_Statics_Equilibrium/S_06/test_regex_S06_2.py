import re

prompt = " - **Goal**: Reach x >= 0.1m beyond the edge."
pattern = r"(\s*-\s*\*\*Goal\*\*: Reach x >= )(\d+\.?\d*)m( beyond the edge\.?)"
new_prompt = re.sub(pattern, f"\\g<1>0.80m (originally 0.10m in the source environment)\\g<3>", prompt)
print(f"Match found: {bool(re.search(pattern, prompt))}")
print(f"Output: '{new_prompt}'")

