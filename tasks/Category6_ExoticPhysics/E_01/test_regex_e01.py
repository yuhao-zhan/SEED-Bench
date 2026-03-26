import re

# Mock base description and patterns used in stages.py
description = """
Design a stable structure that stays within the boundaries of a bounded arena under time-varying gravity.

## Task Environment
- **Arena**: A bounded region with x in [0, 40] m and y in [0, 20] m. 
...
- **Build Zone**: Structure must be built within x=[12.0, 28.0], y=[6.0, 18.0].
...
- **Joint strength**: Joints have no force limit (they do not break from overload).
...
"""

# Regex patterns from stages.py
arena_pattern = r"(- \*\*Arena\*\*: A bounded region with x in \[0, 40\] m and y in \[0, )(\d+\.?\d*)(\] m\.)"
bz_pattern = r"(- \*\*Build Zone\*\*: Structure must be built within x=\[12\.0, 28\.0\], y=\[6\.0, )(\d+\.?\d*)(\]\.|\] \()"
joint_pattern = r"(- \*\*Joint strength\*\*: )Joints have no force limit \(they do not break from overload\)\."

# Test substitutions
target_arena_y_max = 16.8
target_bz_y_max = 16.5
target_joint_limit = 600.0
base_arena_y_max = 20.0
base_bz_y_max = 18.0

print("--- Arena Pattern Match ---")
match_arena = re.search(arena_pattern, description)
print(f"Match: {bool(match_arena)}")
if match_arena:
    new_d = re.sub(arena_pattern, f"\g<1>{target_arena_y_max:.1f}\g<3> (originally y in [0, {base_arena_y_max:.1f}] m in the source environment).", description)
    print(new_d)

print("\n--- Build Zone Pattern Match ---")
match_bz = re.search(bz_pattern, description)
print(f"Match: {bool(match_bz)}")
if match_bz:
    new_d = re.sub(bz_pattern, f"\g<1>{target_bz_y_max:.1f}]. (originally y=[6.0, {base_bz_y_max:.1f}] in the source environment).", description)
    print(new_d)

print("\n--- Joint Pattern Match ---")
match_joint = re.search(joint_pattern, description)
print(f"Match: {bool(match_joint)}")
if match_joint:
    new_d = re.sub(joint_pattern, f"\g<1>Joints break when reaction force exceeds {target_joint_limit:.0f} N (originally no force limit in the source environment).", description)
    print(new_d)
