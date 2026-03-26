from stages import update_task_description_for_visible_changes, update_success_criteria_for_visible_changes, get_s05_curriculum_stages
from prompt import TASK_PROMPT
import re

stages = get_s05_curriculum_stages()
base_desc = TASK_PROMPT['task_description']
base_crit = TASK_PROMPT['success_criteria']
base_config = {} # Empty dict to simulate default fallbacks

for i, stage in enumerate(stages):
    print(f"=== Stage {i+1} ===")
    mutated_desc = update_task_description_for_visible_changes(base_desc, stage['terrain_config'], base_config)
    mutated_crit = update_success_criteria_for_visible_changes(base_crit, stage['terrain_config'], base_config)
    
    print("DESC DIFF:")
    base_lines = base_desc.split('\n')
    mutated_lines = mutated_desc.split('\n')
    for b, m in zip(base_lines, mutated_lines):
        if b != m:
            print(f"- {b}")
            print(f"+ {m}")
            
    print("CRIT DIFF:")
    base_lines = base_crit.split('\n')
    mutated_lines = mutated_crit.split('\n')
    for b, m in zip(base_lines, mutated_lines):
        if b != m:
            print(f"- {b}")
            print(f"+ {m}")
