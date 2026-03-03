import sys
import os
import math

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from tasks.Category1_Statics_Equilibrium.S_04.environment import DaVinciSandbox
from tasks.Category1_Statics_Equilibrium.S_04.evaluator import Evaluator
import tasks.Category1_Statics_Equilibrium.S_04.agent as agent

def debug_stage(stage_id="Stage-1"):
    from tasks.Category1_Statics_Equilibrium.S_04.stages import get_s04_curriculum_stages
    stages = get_s04_curriculum_stages()
    stage = next(s for s in stages if s["stage_id"] == stage_id)
    terrain_config = stage.get("terrain_config", {})
    physics_config = stage.get("physics_config", {})

    sandbox = DaVinciSandbox(terrain_config=terrain_config, physics_config=physics_config)
    
    build_func = getattr(agent, f"build_agent_{stage_id.lower().replace('-', '_')}", agent.build_agent)
    action_func = getattr(agent, f"agent_action_{stage_id.lower().replace('-', '_')}", agent.agent_action)

    agent_body = build_func(sandbox)
    evaluator = Evaluator(sandbox.get_terrain_bounds(), environment=sandbox)
    
    from common.simulator import TIME_STEP
    
    for step in range(30):
        action_func(sandbox, agent_body, step)
        sandbox.step(TIME_STEP)
        
        load_body = sandbox._terrain_bodies.get("load")
        load_y = load_body.position.y if load_body else None
        print(f"Step {step}: load_attached={sandbox._load_attached}, load_y={load_y}")

if __name__ == "__main__":
    debug_stage()