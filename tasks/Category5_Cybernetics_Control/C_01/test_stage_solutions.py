#!/usr/bin/env python3
import os
import sys

# Add root directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from evaluation.verifier import CodeVerifier
from tasks.Category5_Cybernetics_Control.C_01.stages import get_stages

def test_stage(stage_idx, stages_config):
    agent_path = os.path.join(os.path.dirname(__file__), 'agent.py')
    with open(agent_path, 'r') as f:
        code = f.read()
    
    stage = stages_config[stage_idx]
    name = stage["name"]
    build_fn = stage["build_fn"]
    action_fn = stage["action_fn"]
    
    # Replacement logic to make CodeVerifier use the stage-specific functions
    if build_fn != "build_agent":
        code = code.replace("def build_agent(", "def build_agent_old(")
        code = code.replace(f"def {build_fn}(", "def build_agent(")
        
    if action_fn != "agent_action":
        code = code.replace("def agent_action(", "def agent_action_old(")
        code = code.replace(f"def {action_fn}(", "def agent_action(")
    
    config = stage.get("config_overrides", {})
    env_overrides = {
        "physics_config": {
            "gravity": config.get("gravity", 9.8),
            "pole_length": config.get("pole_length", 2.0),
            "pole_damping": config.get("pole_damping", 0.0),
            "pole_start_angle": config.get("pole_start_angle", 0.0),
            "sensor_delay_angle_steps": config.get("sensor_delay_angle_steps", 0),
            "sensor_delay_omega_steps": config.get("sensor_delay_omega_steps", 0)
        }
    }
    
    verifier = CodeVerifier(
        task_name="Category5_Cybernetics_Control/C_01",
        max_steps=config.get("max_steps", 10000),
        env_overrides=env_overrides
    )
    
    print(f"Testing {name}: {stage['description']}...")
    try:
        success, score, metrics, error = verifier.verify_code(code=code, headless=True)
        if success:
            print(f"  Result: PASS, Steps={metrics.get('step_count')}")
        else:
            print(f"  Result: FAIL, Score={score:.2f}, Steps={metrics.get('step_count')}")
            if error:
                print(f"  Error: {error}")
            if metrics.get("failure_reason"):
                print(f"  Reason: {metrics['failure_reason']}")
        return success
    except Exception as e:
        print(f"  CRASHED: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    stages_config = get_stages()
    passed_count = 0
    
    for i in range(len(stages_config)):
        if test_stage(i, stages_config):
            passed_count += 1
            
    print(f"\nFinal Result: {passed_count}/{len(stages_config)} stages passed.")
    if passed_count < len(stages_config):
        sys.exit(1)

if __name__ == "__main__":
    main()
