import re

criteria = "(Tip reaches x >= 0.1m)."
pattern = r"(\(Tip reaches x >= )(\d+\.?\d*)(m\)\.)"
new_criteria = re.sub(pattern, f"\\g<1>0.80m (originally 0.10m in the source environment)).", criteria)
print(f"Match found: {bool(re.search(pattern, criteria))}")
print(f"Output: '{new_criteria}'")

