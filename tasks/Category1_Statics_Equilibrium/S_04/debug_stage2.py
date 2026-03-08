
import sys
import os
import math

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from tasks.Category1_Statics_Equilibrium.S_04.environment import DaVinciSandbox
from tasks.Category1_Statics_Equilibrium.S_04.evaluator import Evaluator
import tasks.Category1_Statics_Equilibrium.S_04.agent as agent

def debug_stage2():
    from tasks.Category1_Statics_Equilibrium.S_04.stages import get_s04_curriculum_stages
    stages = get_s04_curriculum_stages()
    stage = next(s for s in stages if s["stage_id"] == "Stage-2")
    terrain_config = stage.get("terrain_config", {})
    physics_config = stage.get("physics_config", {})

    sandbox = DaVinciSandbox(terrain_config=terrain_config, physics_config=physics_config)
    
    # Use the original build_agent (initial reference solution)
    agent_body = agent.build_agent(sandbox)
    evaluator = Evaluator(sandbox.get_terrain_bounds(), environment=sandbox)
    
    from common.simulator import TIME_STEP
    
    for step in range(200): # Enough to reach current_time > 2.0
        agent.agent_action(sandbox, agent_body, step)
        sandbox.step(TIME_STEP)
        
        if step % 10 == 0:
            beam_angle = sandbox.get_main_beam_angle()
            print(f"Step {step}: Angle={beam_angle * 180 / math.pi:.1f}°")
        
        done, score, metrics = evaluator.evaluate(None, step, 20000)
        if done:
            print(f"Simulation ended at step {step}")
            print(f"Results: success={metrics.get('success')}, score={score}")
            print(f"Failure reason: {metrics.get('failure_reason')}")
            print(f"Beam angle: {metrics.get('beam_angle_deg'):.1f}°")
            print(f"Net torque: {metrics.get('net_torque_about_pivot'):.1f} N·m")
            print(f"COM: x={metrics.get('structure_com_x'):.3f}, y={metrics.get('structure_com_y'):.3f}")
            print(f"Load: {metrics.get('load_pos')}")
            break

if __name__ == "__main__":
    debug_stage2()
