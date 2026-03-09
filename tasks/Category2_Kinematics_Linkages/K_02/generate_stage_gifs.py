import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from evaluation.verifier import CodeVerifier
from tasks.Category2_Kinematics_Linkages.K_02.stages import get_stage_config
import tasks.Category2_Kinematics_Linkages.K_02.agent as agent_mod

def run_stage_verification():
    """
    Verify each stage with its specialized reference solution.
    """
    total_passed = 0
    
    for i in range(1, 5):
        print(f"Generating GIF for Stage-{i}...")
        
        # Override the build_agent and agent_action in agent_mod
        agent_mod.build_agent = getattr(agent_mod, f"build_agent_stage_{i}")
        agent_mod.agent_action = getattr(agent_mod, f"agent_action_stage_{i}")
        
        terrain_config, physics_config, task_desc = get_stage_config(i)
        
        env_overrides = {
            "terrain_config": terrain_config,
            "physics_config": physics_config
        }
        
        verifier = CodeVerifier(
            task_name="Category2_Kinematics_Linkages/K_02",
            max_steps=10000, # Give plenty of time to climb
            env_overrides=env_overrides
        )
        
        success, score, metrics = verifier.verify(
            agent_mod.build_agent,
            agent_mod.agent_action,
            gif_name=f"stage_{i}_solution_success.gif"
        )
        
        print(f"Result for Stage-{i}: Success={success}, Score={score}")
        if not success:
            print(f"Error: {metrics.get('error')}")
            print(f"Metrics: {metrics}")
        else:
            total_passed += 1
        print("-" * 50)

    print(f"Total passed: {total_passed}/4")

if __name__ == "__main__":
    run_stage_verification()
