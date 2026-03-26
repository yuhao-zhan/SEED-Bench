import sys
from stages import update_task_description_for_visible_changes, update_success_criteria_for_visible_changes, DEFAULT_METEOR_COUNT, DEFAULT_METEOR_SPAWN_INTERVAL, DEFAULT_MAX_MASS, DEFAULT_CORE_X, DEFAULT_CORE_Y, DEFAULT_CORE_MAX_FORCE, DEFAULT_MAX_JOINT_FORCE, DEFAULT_MAX_JOINT_TORQUE, DEFAULT_HAS_WALLS
from prompt import TASK_PROMPT

def run_tests():
    desc = TASK_PROMPT['task_description']
    succ = TASK_PROMPT['success_criteria']
    
    print("Testing Bombardment...")
    target_config = {"meteor_count": 24, "meteor_spawn_interval": 15}
    base_config = {"meteor_count": 12, "meteor_spawn_interval": 30}
    desc_out = update_task_description_for_visible_changes(desc, target_config, base_config)
    print("MATCHED BOMBARDMENT:", "24 boulders" in desc_out)
    print("MATCHED BOMBARDMENT TIME LIMIT:", "360 steps" in desc_out)

    print("Testing Mass...")
    target_config = {"max_structure_mass": 200.0}
    base_config = {"max_structure_mass": 300.0}
    desc_out = update_task_description_for_visible_changes(desc, target_config, base_config)
    succ_out = update_success_criteria_for_visible_changes(succ, target_config, base_config)
    print("MATCHED MASS DESC:", "200.0 kg" in desc_out)
    print("MATCHED MASS SUCC:", "200.0 kg" in succ_out)
    
    print("Testing Core Pos...")
    target_config = {"core_x": 5.0, "core_y": 2.0}
    base_config = {"core_x": 10.0, "core_y": 1.0}
    desc_out = update_task_description_for_visible_changes(desc, target_config, base_config)
    succ_out = update_success_criteria_for_visible_changes(succ, target_config, base_config)
    print("MATCHED CORE POS DESC INTRO:", "x=5.0, y=2.0" in desc_out)
    print("MATCHED CORE POS DESC ENV:", "(5.0, 2.0)" in desc_out)
    print("MATCHED CORE POS DESC KOZ:", "1.3m of the core center (5.0, 2.0)" in desc_out)
    print("MATCHED CORE POS SUCC KOZ:", "distance to (5.0, 2.0) must be >= 1.3m" in succ_out)

    print("Testing Core Force...")
    target_config = {"max_core_force": 100.0}
    base_config = {"max_core_force": 150.0}
    desc_out = update_task_description_for_visible_changes(desc, target_config, base_config)
    succ_out = update_success_criteria_for_visible_changes(succ, target_config, base_config)
    print("MATCHED CORE FORCE DESC:", "exceeds 100.0 N" in desc_out)
    print("MATCHED CORE FORCE SUCC:", "100.0 N" in succ_out)
    
    print("Testing Joint Limits...")
    target_config = {"max_joint_force": 5000.0, "max_joint_torque": 8000.0}
    base_config = {"max_joint_force": 1e12, "max_joint_torque": 1e12}
    desc_out = update_task_description_for_visible_changes(desc, target_config, base_config)
    print("MATCHED JOINT FORCE:", "5000.0 N" in desc_out)
    print("MATCHED JOINT TORQUE:", "8000.0 Nm" in desc_out)
    if "5000.0 N" not in desc_out or "8000.0 Nm" not in desc_out:
        print("DESC_OUT JOINT LIMITS:")
        print(desc_out)

    print("Testing Lateral boundaries...")
    target_config = {"has_walls": True}
    base_config = {"has_walls": False}
    desc_out = update_task_description_for_visible_changes(desc, target_config, base_config)
    succ_out = update_success_criteria_for_visible_changes(succ, target_config, base_config)
    print("MATCHED WALLS DESC:", "enclosed by lateral walls" in desc_out)
    print("MATCHED WALLS SUCC:", "enclosed by lateral walls" in succ_out)

run_tests()
