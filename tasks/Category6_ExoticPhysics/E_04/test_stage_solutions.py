#!/usr/bin/env python3
import os
import sys
import importlib.util

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from evaluation.verifier import CodeVerifier

def load_stages():
    stages_file = os.path.join(os.path.dirname(__file__), "stages.py")
    spec = importlib.util.spec_from_file_location("e04_stages", stages_file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "get_e04_curriculum_stages")()

def main():
    task_name = "Category6_ExoticPhysics/E_04"
    max_steps = 12000  # align with prompt and environment.MAX_STEPS
    agent_path = os.path.join(os.path.dirname(__file__), "agent.py")
    with open(agent_path, "r") as f:
        code = f.read()

    stages = load_stages()
    
    # We want to test a specific stage
    if len(sys.argv) > 1:
        target_stage = sys.argv[1] # e.g., "Stage-1"
    else:
        target_stage = None

    for stage in stages:
        stage_id = stage["stage_id"]
        if target_stage and stage_id != target_stage:
            continue
            
        print(f"=== Testing {stage_id}: {stage.get('title', '')} ===")
        
        env_overrides = {
            "terrain_config": stage.get("terrain_config") or {},
            "physics_config": stage.get("physics_config") or {},
        }
        
        # We need to tell the verifier to use the stage-specific build_agent and agent_action
        # CodeVerifier usually calls build_agent and agent_action.
        # We can wrap the code to call the correct ones.
        
        stage_num = stage_id.split("-")[1]
        wrapper_code = code + f"""
def build_agent(sandbox):
    return build_agent_stage_{stage_num}(sandbox)

def agent_action(sandbox, agent_body, step_count):
    return agent_action_stage_{stage_num}(sandbox, agent_body, step_count)
"""
        
        verifier = CodeVerifier(task_name=task_name, max_steps=max_steps, env_overrides=env_overrides)
        success, score, metrics, error = verifier.verify_code(wrapper_code, headless=True, save_gif_path=None)
        
        print("Success:", success, "| Score:", score)
        if metrics.get("failure_reason"):
            print("Failure reason:", metrics["failure_reason"])
        if metrics:
            print("Metrics:", {k: v for k, v in metrics.items() if k not in ['failure_reason']})
        if error:
            print("Error:", error)
        print()

if __name__ == "__main__":
    main()
