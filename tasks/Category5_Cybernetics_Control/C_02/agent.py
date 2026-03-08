import math

class BaselineLanderAgent:
    def __init__(self, agent_body):
        self.agent_body = agent_body
        self.x_prev = None
        self.y_prev = None
        self.DT = 1.0 / 60.0
    @property
    def position(self): return self.agent_body.position
    @property
    def linearVelocity(self): return self.agent_body.linearVelocity
    def act(self, sandbox, step_count):
        pos = sandbox.get_lander_position()
        x, y = pos[0], pos[1]
        angle = sandbox.get_lander_angle()
        omega = sandbox.get_lander_angular_velocity()
        if self.x_prev is not None:
            vx = (x - self.x_prev) / self.DT
            vy = (y - self.y_prev) / self.DT
        else:
            v_real = self.agent_body.linearVelocity
            vx, vy = v_real.x, v_real.y
        self.x_prev, self.y_prev = x, y
        t_sim = step_count * self.DT
        plat_x = 17.0 + 1.8 * math.sin(2.0 * math.pi * t_sim / 6.0)
        if x < 10.2:
            target_x = 11.5
            target_y = 10.5
        elif x < 13.5:
            target_x = 14.0
            target_y = 7.5
        else:
            target_x = plat_x - 2.0
            target_y = 1.05
        target_vy = 2.0 * (target_y - y)
        target_vy = max(-3.5, min(3.0, target_vy))
        thrust = 500.0 + 350.0 * (target_vy - vy)
        thrust = max(0.0, min(600.0, thrust))
        target_vx = 3.0 * (target_x - x)
        target_vx = max(-4.0, min(4.0, target_vx))
        target_angle = -0.4 * (target_vx - vx)
        target_angle = max(-0.5, min(0.5, target_angle))
        if y < 4.0:
            target_angle = 0.0
        torque = 600.0 * (target_angle - angle) - 200.0 * omega
        torque = max(-120.0, min(120.0, torque))
        sandbox.apply_thrust(thrust, torque)

def build_agent(sandbox):
    return BaselineLanderAgent(sandbox.get_lander_body())

def agent_action(sandbox, agent, step_count):
    agent.act(sandbox, step_count)
