import os
import sys
import importlib.util
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from evaluation.prompt import load_task_prompt

def test_task_transition(task_name: str, stage_i_id: str, stage_j_id: str):
    print(f"\n{'='*20} Testing {task_name}: {stage_i_id} -> {stage_j_id} {'='*20}")
    
    # 1. Load base prompt
    try:
        base_prompt = load_task_prompt(task_name)
    except Exception as e:
        print(f"Error loading prompt for {task_name}: {e}")
        return

    # 2. Get task directory and stages
    from evaluation.prompt import parse_task_name
    task_path, _ = parse_task_name(task_name)
    task_dir = os.path.join('tasks', task_path)
    stages_file = os.path.join(task_dir, 'stages.py')
    
    # 3. Load stages module
    spec = importlib.util.spec_from_file_location("task_stages", stages_file)
    stages_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stages_mod)
    
    # Find the stages function (e.g., get_s01_curriculum_stages)
    stages_func = None
    for name in dir(stages_mod):
        if name.startswith('get_') and name.endswith('_stages'):
            stages_func = getattr(stages_mod, name)
            break
    
    if not stages_func:
        print(f"Could not find stages function in {stages_file}")
        return
        
    stages = stages_func()
    
    # Helper to get config by stage_id
    def get_stage_config(sid):
        if sid == "Initial":
            return {"terrain_config": {}, "physics_config": {}}
        for s in stages:
            if s["stage_id"] == sid:
                return s
        return None

    stage_i = get_stage_config(stage_i_id)
    stage_j = get_stage_config(stage_j_id)
    
    if not stage_i or not stage_j:
        print(f"Could not find stage configs for {stage_i_id} or {stage_j_id}")
        return

    # 4. Get update functions
    update_desc_func = getattr(stages_mod, 'update_task_description_for_visible_changes', None)
    update_criteria_func = getattr(stages_mod, 'update_success_criteria_for_visible_changes', None)
    
    desc = base_prompt.get("task_description", "")
    criteria = base_prompt.get("success_criteria", "")
    
    target_terrain = stage_j.get("terrain_config", {})
    base_terrain = stage_i.get("terrain_config", {})
    
    # 5. Run updates
    if update_desc_func:
        desc = update_desc_func(desc, target_terrain, base_terrain)
    if update_criteria_func:
        criteria = update_criteria_func(criteria, target_terrain, base_terrain)
        
    # Add suffix if it exists in target
    suffix = stage_j.get("task_description_suffix", "")
    if suffix:
        desc += "\n" + suffix

    # 6. Print results (only changed parts for brevity)
    print("\n--- UPDATED DESCRIPTION (Relevant Parts) ---")
    lines = desc.split('\n')
    for line in lines:
        if "(FROM:" in line or "## Environmental" in line or "## Arena" in line:
            print(line)
            
    print("\n--- UPDATED SUCCESS CRITERIA (Relevant Parts) ---")
    lines = criteria.split('\n')
    for line in lines:
        if "(FROM:" in line:
            print(line)

if __name__ == "__main__":
    # Test cases
    # 1. S_01: Initial -> Stage-1 (Gap increase)
    test_task_transition("Category1_Statics_Equilibrium/S_01", "Initial", "Stage-1")
    
    # 2. S_01: Stage-1 -> Stage-2 (Gap decrease + invisible change)
    test_task_transition("Category1_Statics_Equilibrium/S_01", "Stage-1", "Stage-2")
    
    # 3. S_04: Initial -> Stage-4 (Multiple visible/invisible)
    test_task_transition("Category1_Statics_Equilibrium/S_04", "Initial", "Stage-4")
    
    # 4. S_01: Stage-3 -> Stage-4 (Invisible change only)
    test_task_transition("Category1_Statics_Equilibrium/S_01", "Stage-3", "Stage-4")
    
    # 5. K_05: Stage-3 -> Stage-4 (Target height change)
    test_task_transition("Category2_Kinematics_Linkages/K_05", "Stage-3", "Stage-4")
    
    # 6. E_01: Initial -> Stage-1 (Arena shrink)
    test_task_transition("Category6_ExoticPhysics/E_01", "Initial", "Stage-1")
