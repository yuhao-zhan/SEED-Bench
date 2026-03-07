import sys
sys.path.insert(0, '.')
from tasks.Category5_Cybernetics_Control.C_02.environment import Sandbox

import math

class FixedLanderAgent:
    def __init__(self, agent_body):
        self.agent_body = agent_body
        self.x_prev = None
        self.y_prev = None
        self.vx_est = 0.0
        self.vy_est = 0.0
        self.DT = 1.0 / 60.0

    def act(self, sandbox, step_count):
        pos = sandbox.get_lander_position()
        x, y = pos[0], pos[1]
        angle = sandbox.get_lander_angle()
        omega = sandbox.get_lander_angular_velocity()

        if self.x_prev is not None:
            self.vx_est = (x - self.x_prev) / self.DT
            self.vy_est = (y - self.y_prev) / self.DT
        self.x_prev, self.y_prev = x, y
        vx, vy = self.vx_est, self.vy_est

        t_sim = step_count * self.DT
        plat_x = 17.0 + 1.8 * math.sin(2.0 * math.pi * t_sim / 6.0)

        # Tune to take ~400 steps, using around 4000 fuel. 
        # This will leave ~1500 fuel in baseline (requires 450).
        # But if total fuel becomes 3600 (mutated stage 2), it will run out.
        if step_count < 140: # Extended hover to burn more fuel
            target_x = 6.0
            target_y = 11.5
        elif x < 15.0:
            target_x = 17.5
            target_y = 7.0 
        else:
            target_x = plat_x
            target_y = 1.25

        # Altitude
        target_vy = 1.5 * (target_y - y)
        target_vy = max(-3.0, min(3.0, target_vy)) 

        thrust = 500.0 + 350.0 * (target_vy - vy)
        thrust = max(0.0, min(600.0, thrust))

        # Horizontal
        target_vx = 1.5 * (target_x - x) 
        target_vx = max(-3.5, min(3.5, target_vx))
        
        target_angle = -0.3 * (target_vx - vx)
        target_angle = max(-0.55, min(0.55, target_angle)) 
        
        if y < 3.0: 
            target_angle = 0.0

        torque = 600.0 * (target_angle - angle) - 200.0 * omega
        torque = max(-120.0, min(120.0, torque))

        sandbox.apply_thrust(thrust, torque)

s = Sandbox()
agent = FixedLanderAgent(s.get_lander_body())

fuel_start = s.get_remaining_fuel()
for step in range(1, 1000):
    agent.act(s, step)
    s.step(1/60.0)
    pos = s.get_lander_position()
    v = s._get_lander_velocity()
    if pos[1] <= 1.55:
        print(f"Landed at step {step}: vy={v[1]:.2f}, fuel_used={fuel_start - s.get_remaining_fuel():.2f}")
        break
