
import os
import sys

# Add scripts dir to path
sys.path.insert(0, "/Users/zhanyuxiao/Desktop/GitHub/SEED-Bench")

from evaluation.evaluate_cross_mutated import get_reference_solution

task_name = "Category5_Cybernetics_Control/C_06"
for stage_id in ["Initial", "Stage-1", "Stage-2", "Stage-3", "Stage-4"]:
    print(f"--- {stage_id} ---")
    try:
        code = get_reference_solution(task_name, stage_id)
        print(f"Has build_agent: {'def build_agent(' in code}")
        print(f"Has agent_action: {'def agent_action(' in code}")
        # print(code[:200])
        print("...")
        print(code[-200:])
    except Exception as e:
        print(f"Error: {e}")
