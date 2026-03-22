
import sys
import os
import math

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from tasks.Category5_Cybernetics_Control.C_05.environment import Sandbox
from tasks.Category5_Cybernetics_Control.C_05.agent import build_agent_stage_2, agent_action_stage_2, _step_when_a_triggered_s2

def debug_stage2():
    # Match `stages.py` Stage-2 (`get_c05_curriculum_stages` second entry)
    physics_config = {
        "trigger_stay_steps": 300,
        "speed_cap_inside": 0.05,
        "repulsion_mag": 40.0,
        "recent_a_for_b": 5000,
        "recent_b_for_c": 5000,
        "c_high_history": 5000,
    }
    
    # Reset global state
    _step_when_a_triggered_s2[0] = None
    
    sandbox = Sandbox(physics_config=physics_config)
    agent_body = build_agent_stage_2(sandbox)
    
    max_steps = 15000
    b_triggered_at = None
    
    print(f"{'Step':>5} | {'Pos':>12} | {'Vel':>12} | {'Force':>12} | {'Next':>5} | {'Triggers':>10} | {'StepsInZ':>8}")
    print("-" * 80)
    
    for step in range(max_steps):
        # Run agent action
        agent_action_stage_2(sandbox, agent_body, step)
        
        # Get state BEFORE sandbox.step() processes the force
        pos = sandbox.get_agent_position()
        vel = sandbox.get_agent_velocity()
        next_sw = sandbox.get_next_required_switch()
        triggers = sandbox.get_triggered_switches()
        steps_in_z = sandbox.get_steps_in_current_zone()
        
        # We need to peek at the force that was just applied
        fx, fy = sandbox._force_x, sandbox._force_y
        
        if "B" in triggers and b_triggered_at is None:
            b_triggered_at = step
            print(f"--- B TRIGGERED AT STEP {step} ---")
            
        if b_triggered_at is not None and step <= b_triggered_at + 1000:
            if step % 20 == 0 or step == b_triggered_at:
                print(f"{step:5d} | ({pos[0]:5.2f},{pos[1]:5.2f}) | ({vel[0]:5.2f},{vel[1]:5.2f}) | ({fx:5.2f},{fy:5.2f}) | {next_sw if next_sw else 'None':5s} | {str(triggers):10s} | {steps_in_z:8d}")
        
        if "C" in triggers:
            print(f"--- C TRIGGERED AT STEP {step} ---")
            break
            
        sandbox.step(1.0/60.0)
        
    print(f"Final triggers: {sandbox.get_triggered_switches()}")

if __name__ == "__main__":
    debug_stage2()
