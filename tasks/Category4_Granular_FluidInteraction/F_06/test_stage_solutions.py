import os
import sys
import json

# Add the root directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from evaluation.verifier import CodeVerifier
from tasks.Category4_Granular_FluidInteraction.F_06.stages import get_f06_curriculum_stages

def test_stage(stage_index):
    task_name = "Category4_Granular_FluidInteraction/F_06"
    agent_file = os.path.join(os.path.dirname(__file__), "agent.py")
    
    stage_name = f"Stage-{stage_index}"
    print(f"\n=== Testing {stage_name} ===")
    
    with open(agent_file, 'r') as f:
        original_code = f.read()
    
    wrapper_code = original_code + f"""
build_agent = build_agent_stage_{stage_index}
agent_action = agent_action_stage_{stage_index}
"""
    
    temp_agent_file = os.path.join(os.path.dirname(__file__), f"temp_agent_stage_{stage_index}.py")
    with open(temp_agent_file, 'w') as f:
        f.write(wrapper_code)
    
    try:
        stages = get_f06_curriculum_stages()
        stage_config = stages[stage_index-1]
        
        env_overrides = {
            'terrain_config': stage_config.get('terrain_config', {}),
            'physics_config': stage_config.get('physics_config', {})
        }
        
        # Using 200000 steps as per the updated stages.py
        verifier = CodeVerifier(task_name, max_steps=200000, env_overrides=env_overrides)
        
        success, score, metrics, error = verifier.verify_code(code=wrapper_code, headless=True)
        
        print(f"Results for {stage_name}: Success={success}, Score={score}")
        if metrics and 'delivery_ratio_percent' in metrics:
            print(f"  Delivery Ratio: {metrics.get('delivery_ratio_percent'):.1f}%")
            print(f"  Force Budget: {metrics.get('force_budget')}")
        if not success:
            print(f"  Error/Failure: {error}")
            if metrics and 'failure_reason' in metrics:
                print(f"  Failure Reason: {metrics.get('failure_reason')}")
        return success
    except Exception as e:
        print(f"Exception during test: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(temp_agent_file):
            os.remove(temp_agent_file)

if __name__ == "__main__":
    all_success = True
    for i in range(1, 5):
        if not test_stage(i):
            all_success = False
    
    if all_success:
        print("\nAll stages passed!")
        sys.exit(0)
    else:
        print("\nSome stages failed.")
        sys.exit(1)
