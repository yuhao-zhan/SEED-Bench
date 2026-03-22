
import sys
import os
import math

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from tasks.Category5_Cybernetics_Control.C_05.environment import Sandbox
from tasks.Category5_Cybernetics_Control.C_05.agent import build_agent_stage_1, agent_action_stage_1, _step_when_a_triggered_s1

def debug_stage1():
    # Match `stages.py` Stage-1 (`get_c05_curriculum_stages` first entry)
    physics_config = {
        "speed_cap_inside": 0.05,
        "recent_a_for_b": 5000,
        "recent_b_for_c": 5000,
        "c_high_history": 5000,
    }
    
    # Reset global state
    _step_when_a_triggered_s1[0] = None
    
    sandbox = Sandbox(physics_config=physics_config)
    agent_body = build_agent_stage_1(sandbox)
    
    max_steps = 15000
    b_entered_at = None
    
    print(f"{'Step':>5} | {'Pos':>12} | {'Vel':>12} | {'Speed':>7} | {'Next':>5} | {'StepsInZ':>8}")
    print("-" * 70)
    
    for step in range(max_steps):
        # Run agent action
        agent_action_stage_1(sandbox, agent_body, step)
        
        # Get state
        pos = sandbox.get_agent_position()
        vel = sandbox.get_agent_velocity()
        speed = math.sqrt(vel[0]**2 + vel[1]**2)
        next_sw = sandbox.get_next_required_switch()
        triggers = sandbox.get_triggered_switches()
        steps_in_z = sandbox.get_steps_in_current_zone()
        
        if next_sw == "B" and steps_in_z > 0 and b_entered_at is None:
            b_entered_at = step
            print(f"--- ENTERED B AT STEP {step} ---")
            
        if b_entered_at is not None and step <= b_entered_at + 1000:
            if step % 20 == 0 or step == b_entered_at:
                print(f"{step:5d} | ({pos[0]:5.2f},{pos[1]:5.2f}) | ({vel[0]:5.2f},{vel[1]:5.2f}) | {speed:7.4f} | {next_sw:5s} | {steps_in_z:8d}")
        
        if "B" in triggers:
            print(f"--- B TRIGGERED AT STEP {step} ---")
            break
            
        sandbox.step(1.0/60.0)
        
    print(f"Final triggers: {sandbox.get_triggered_switches()}")

if __name__ == "__main__":
    debug_stage1()
