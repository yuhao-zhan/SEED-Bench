import os
import sys
import math

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from tasks.Category5_Cybernetics_Control.C_01.environment import Sandbox
from tasks.Category5_Cybernetics_Control.C_01.evaluator import Evaluator
from tasks.Category5_Cybernetics_Control.C_01.agent import build_agent_stage_1, agent_action_stage_1

def debug_stage():
    from tasks.Category5_Cybernetics_Control.C_01.stages import get_stages
    stages = get_stages()
    stage = stages[1] # Stage 1
    config = stage.get("config_overrides", {})
    
    env = Sandbox(physics_config=config)
    agent_body = build_agent_stage_1(env)
    evaluator = Evaluator(env.get_terrain_bounds(), environment=env)
    
    max_steps = 1500
    
    for i in range(max_steps):
        agent_action_stage_1(env, agent_body, i)
        env.step(1.0/60.0)
        done, score, metrics = evaluator.evaluate(agent_body, i, max_steps)
        
        theta = env.get_true_pole_angle()
        omega = env.get_pole_angular_velocity()
        x = env.get_cart_position()
        v = env.get_cart_velocity()
        bal = metrics.get('balance_achieved')
        
        gravity = config.get("gravity", 9.8)
        pole_length = config.get("pole_length", 2.0)
        E = 0.5 * omega**2 + (gravity / (pole_length / 2.0)) * (math.cos(theta) - 1.0)
        
        if i >= 250 and i <= 280:
            print(f"Step {i:4d}: th={theta:6.3f} om={omega:6.3f} E={E:6.2f} x={x:6.2f} bal={bal}")
            
        if done:
            print(f"DONE at step {i}: success={metrics.get('success')}, reason={metrics.get('failure_reason')}")
            break

if __name__ == "__main__":
    debug_stage()
