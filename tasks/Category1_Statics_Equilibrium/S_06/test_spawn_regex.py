import re

prompt = "- **Spawn Rule**: Blocks must be initialized within the permitted build access zone: x in [-10.0, 0.0]."
pattern = r"(\s*-\s*\*\*Spawn Rule\*\*: Blocks must be initialized within the permitted build access zone: x in )(\[.*?\])(\.?)"
target_spawn = [-10.0, 0.4]
base_str = "[-10.0, 0.0]"
new_prompt = re.sub(pattern, f"\\g<1>[{target_spawn[0]:.1f}, {target_spawn[1]:.1f}] (originally {base_str} in the source environment)\\g<3>", prompt)
print(f"Match found: {bool(re.search(pattern, prompt))}")
print(f"Output: '{new_prompt}'")
