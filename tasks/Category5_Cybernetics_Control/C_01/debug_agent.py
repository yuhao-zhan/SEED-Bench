
import math
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from tasks.Category5_Cybernetics_Control.C_01.environment import Sandbox
from tasks.Category5_Cybernetics_Control.C_01.agent import build_agent, agent_action

def debug():
    sandbox = Sandbox()
    agent = build_agent(sandbox)
    
    print(f"{'Step':>4} | {'Theta':>7} | {'Omega':>7} | {'X':>7} | {'V':>7} | {'Force':>7} | {'State'}")
    print("-" * 60)
    
    for i in range(100):
        # We need to capture the force applied
        # Since apply_cart_force just sets a variable in sandbox, we can check it
        agent_action(sandbox, agent, i)
        force = sandbox._cart_force_x
        
        pole = sandbox.get_pole_body()
        cart = sandbox.get_cart_body()
        theta = (pole.angle + math.pi) % (2 * math.pi) - math.pi
        omega = pole.angularVelocity
        x = cart.position.x
        v = cart.linearVelocity.x
        
        state = agent.controller.state if hasattr(agent, 'controller') else "N/A"
        is_baseline = agent.controller.is_baseline if hasattr(agent, 'controller') else "N/A"
        
        print(f"{i:4} | {theta:7.3f} | {omega:7.3f} | {x:7.3f} | {v:7.3f} | {force:7.1f} | {state} (B:{is_baseline})")
        
        sandbox.step(1.0/60.0)

if __name__ == "__main__":
    debug()
