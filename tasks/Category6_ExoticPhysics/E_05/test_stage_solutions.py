
import sys
import os
import math
import Box2D

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from tasks.Category6_ExoticPhysics.E_05.environment import Sandbox
from tasks.Category6_ExoticPhysics.E_05.evaluator import Evaluator
from tasks.Category6_ExoticPhysics.E_05.stages import get_e05_curriculum_stages
import tasks.Category6_ExoticPhysics.E_05.agent as agent

def run_one_stage(stage_config, build_func, action_func, max_steps=10000):
    print(f"\n=== Testing {stage_config['stage_id']} ({stage_config['title']}) ===")
    sandbox = Sandbox(
        terrain_config=stage_config.get("terrain_config", {}),
        physics_config=stage_config.get("physics_config", {})
    )
    agent_body = build_func(sandbox)
    evaluator = Evaluator(sandbox.get_terrain_bounds(), environment=sandbox)
    
    time_step = 1.0 / 60.0
    for i in range(max_steps):
        action_func(sandbox, agent_body, i)
        sandbox.step(time_step)
        done, score, metrics = evaluator.evaluate(agent_body, i, max_steps)
        if i % 1000 == 0:
            pos = sandbox.get_body_position()
            print(f"  Step {i}: pos={pos}")
        if done:
            break
    
    print(f"Result: score={score}, success={metrics['success']}, steps={i}")
    if not metrics['success']:
        print(f"Failure reason: {metrics['failure_reason']}")
    return metrics['success']

if __name__ == "__main__":
    stages = get_e05_curriculum_stages()
    
    successes = []
    
    # Stage 1
    s1 = stages[0]
    successes.append(run_one_stage(s1, agent.build_agent_stage_1, agent.agent_action_stage_1))
    
    # Stage 2
    s2 = stages[1]
    successes.append(run_one_stage(s2, agent.build_agent_stage_2, agent.agent_action_stage_2))
    
    # Stage 3
    s3 = stages[2]
    successes.append(run_one_stage(s3, agent.build_agent_stage_3, agent.agent_action_stage_3))
    
    # Stage 4
    s4 = stages[3]
    successes.append(run_one_stage(s4, agent.build_agent_stage_4, agent.agent_action_stage_4))
    
    if all(successes):
        print("\n✅ All mutated stages passed!")
        sys.exit(0)
    else:
        print("\n❌ Some stages failed.")
        sys.exit(1)
