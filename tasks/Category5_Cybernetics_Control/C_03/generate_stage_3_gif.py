#!/usr/bin/env python3
import os
import sys
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.simulator import Simulator, TIME_STEP
from tasks.Category5_Cybernetics_Control.C_03.environment import Sandbox
from tasks.Category5_Cybernetics_Control.C_03.renderer import C03Renderer
from tasks.Category5_Cybernetics_Control.C_03.stages import get_c03_curriculum_stages
from tasks.Category5_Cybernetics_Control.C_03.agent import build_agent_stage_3, agent_action_stage_3

def generate_stage_3_gif():
    print("Generating stage_3_solution_success.gif for C-03 Stage 3...")
    stages = get_c03_curriculum_stages()
    stage_3_cfg = [s for s in stages if s['stage_id'] == 'Stage-3'][0]
    
    simulator = Simulator()
    can_display = simulator.init_display(headless=True, save_gif=True)
    if not can_display:
        print("Error: Cannot initialize display for GIF generation")
        return False
        
    env = Sandbox(terrain_config=stage_3_cfg['terrain_config'], physics_config=stage_3_cfg['physics_config'])
    agent_body = build_agent_stage_3(env)
    renderer = C03Renderer(simulator)
    
    max_steps = 8000
    frame_interval = 20 # Every 20 steps to keep it reasonably sized
    
    for step in range(max_steps):
        agent_action_stage_3(env, agent_body, step)
        if step % frame_interval == 0:
            renderer.render(env, agent_body, 15.0, 0)
            simulator.collect_frame(step, frame_interval=frame_interval)
        env.step(TIME_STEP)
        
    gif_path = os.path.join(os.path.dirname(__file__), "stage_3_solution_success.gif")
    success = simulator.save_gif_animation(gif_path, duration=50)
    simulator.quit()
    if success:
        print(f"Stage 3 success GIF saved: {gif_path}")
    else:
        print("Failed to save GIF")
    return success

if __name__ == "__main__":
    generate_stage_3_gif()
