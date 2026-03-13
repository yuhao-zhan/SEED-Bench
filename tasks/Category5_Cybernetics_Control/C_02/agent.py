import math

class BaselineLanderAgent:
    def __init__(self, agent_body):
        self.agent_body = agent_body
        self.DT = 1.0 / 60.0
    @property
    def position(self): return self.agent_body.position
    @property
    def linearVelocity(self): return self.agent_body.linearVelocity
    def act(self, sandbox, step_count):
        pos = self.agent_body.position
        vel = self.agent_body.linearVelocity
        x, y = pos.x, pos.y
        vx, vy = vel.x, vel.y
        angle = self.agent_body.angle
        omega = self.agent_body.angularVelocity
        t_sim = step_count * self.DT
        t_lead = t_sim + 0.3
        plat_x_now = 17.0 + 1.8 * math.sin(2.0 * math.pi * t_sim / 6.0)
        plat_x_lead = 17.0 + 1.8 * math.sin(2.0 * math.pi * t_lead / 6.0)
        plat_vx = (plat_x_lead - plat_x_now) / 0.3
        if x < 10.5:
            target_x, target_y = 11.5, 11.0
            target_vx = 3.5
        elif x < 14.5:
            target_x, target_y = 15.5, 11.0
            target_vx = 3.5
        else:
            target_x = plat_x_now
            target_y = 1.05
            target_vx = plat_vx + 1.5 * (target_x - x)
        target_vy = 1.5 * (target_y - y)
        if y < 5.0:
            target_vy = max(-0.8, min(1.0, target_vy))
        else:
            target_vy = max(-2.5, min(2.5, target_vy))
        thrust = 500.0 + 500.0 * (target_vy - vy)
        thrust /= max(0.5, math.cos(angle))
        thrust = max(0.0, min(600.0, thrust))
        target_vx = max(-5.0, min(5.0, target_vx))
        target_angle = -0.3 * (target_vx - vx)
        target_angle = max(-0.6, min(0.6, target_angle))
        if y < 4.0:
            target_angle = 0.0
            target_vx = 0.0 if y < 2.5 else target_vx
        torque = 800.0 * (target_angle - angle) - 200.0 * omega
        torque = max(-120.0, min(120.0, torque))
        sandbox.apply_thrust(thrust, torque)

def build_agent(sandbox): return BaselineLanderAgent(sandbox.get_lander_body())

def agent_action(sandbox, agent, step_count): agent.act(sandbox, step_count)

class Stage1LanderAgent(BaselineLanderAgent):
    def act(self, sandbox, step_count):
        pos = self.agent_body.position
        vel = self.agent_body.linearVelocity
        x, y = pos.x, pos.y
        vx, vy = vel.x, vel.y
        angle = self.agent_body.angle
        omega = self.agent_body.angularVelocity
        t_sim = step_count * self.DT
        t_lead = t_sim + 0.3
        plat_x_now = 17.0 + 1.8 * math.sin(2.0 * math.pi * t_sim / 6.0)
        plat_x_lead = 17.0 + 1.8 * math.sin(2.0 * math.pi * t_lead / 6.0)
        plat_vx = (plat_x_lead - plat_x_now) / 0.3
        if x < 15.5:
            target_x, target_y = 16.0, 8.5
            target_vx = 5.5
            target_vy = 1.5 * (target_y - y)
        else:
            target_x = max(15.5, plat_x_now)
            target_y = 1.05
            target_vx = plat_vx + 1.5 * (target_x - x)
            if y < 3.5:
                target_vy = -0.09 - 1.0 * (y - 1.3)
            else:
                target_vy = -3.5
        if y < 3.0:
            target_vx = 0.0
        thrust = 500.0 + 1500.0 * (target_vy - vy)
        thrust /= max(0.5, math.cos(angle))
        thrust = max(0.0, min(600.0, thrust))
        target_vx = max(-6.5, min(6.5, target_vx))
        target_angle = -0.25 * (target_vx - vx)
        target_angle = max(-0.6, min(0.6, target_angle))
        if y < 3.0:
            target_angle = 0.0
        torque = 1000.0 * (target_angle - angle) - 250.0 * omega
        torque = max(-120.0, min(120.0, torque))
        sandbox.apply_thrust(thrust, torque)

def build_agent_Stage_1(sandbox): return Stage1LanderAgent(sandbox.get_lander_body())

def agent_action_Stage_1(sandbox, agent, step_count): agent.act(sandbox, step_count)

class Stage2LanderAgent(BaselineLanderAgent):
    def act(self, sandbox, step_count):
        delay_t = 0.2
        pos = self.agent_body.position
        vel = self.agent_body.linearVelocity
        x, y = pos.x, pos.y
        vx, vy = vel.x, vel.y
        angle = self.agent_body.angle
        omega = self.agent_body.angularVelocity
        x_pred = x + vx * delay_t
        y_pred = y + vy * delay_t - 0.5 * 10.0 * (delay_t**2)
        vx_pred = vx
        vy_pred = vy - 10.0 * delay_t
        angle_pred = angle + omega * delay_t
        t_pred = (step_count + 12) * self.DT
        plat_x_pred = 17.0 + 1.8 * math.sin(2.0 * math.pi * t_pred / 6.0)
        if x_pred < 15.5:
            target_x, target_y = 16.0, 13.0
            target_vx = 2.0
        else:
            target_x = max(15.5, plat_x_pred)
            target_y = 1.05
            target_vx = 1.0 * (target_x - x_pred)
        target_vy = 1.2 * (target_y - y_pred)
        target_vy = max(-1.2, min(1.2, target_vy))
        thrust = 550.0 + 800.0 * (target_vy - vy_pred)
        if step_count < 40: thrust = 600.0
        thrust /= max(0.8, math.cos(angle_pred))
        thrust = max(0.0, min(600.0, thrust))
        target_vx = max(-3.0, min(3.0, target_vx))
        target_angle = -0.15 * (target_vx - vx_pred)
        target_angle = max(-0.25, min(0.25, target_angle))
        if y_pred < 5.0 or step_count < 60:
            target_angle = 0.0
            if y_pred < 3.0: target_vx = 0.0
        torque = 400.0 * (target_angle - angle_pred) - 150.0 * omega
        torque = max(-120.0, min(120.0, torque))
        sandbox.apply_thrust(thrust, torque)

def build_agent_Stage_2(sandbox): return Stage2LanderAgent(sandbox.get_lander_body())

def agent_action_Stage_2(sandbox, agent, step_count): agent.act(sandbox, step_count)

class Stage3LanderAgent(BaselineLanderAgent):
    def act(self, sandbox, step_count):
        pos = self.agent_body.position
        vel = self.agent_body.linearVelocity
        x, y = pos.x, pos.y
        vx, vy = vel.x, vel.y
        angle = self.agent_body.angle
        omega = self.agent_body.angularVelocity
        g = 10.0 if step_count < 150 else 18.0
        hover_thrust = 50.0 * g
        max_thrust = 1200.0
        t_sim = step_count * self.DT
        plat_x = 17.0 + 1.8 * math.sin(2.0 * math.pi * t_sim / 6.0)
        if x < 16.0:
            target_x, target_y = 16.5, 11.5
            target_vx = 6.0
        else:
            target_x = max(16.0, plat_x)
            target_y = 1.05
            target_vx = 2.5 * (target_x - x)
        target_vy = 2.5 * (target_y - y)
        target_vy = max(-4.5, min(4.5, target_vy))
        thrust = hover_thrust + 1200.0 * (target_vy - vy)
        thrust /= max(0.5, math.cos(angle))
        thrust = max(0.0, min(max_thrust, thrust))
        target_vx = max(-8.0, min(8.0, target_vx))
        target_angle = -0.1 * (target_vx - vx)
        target_angle = max(-0.5, min(0.5, target_angle))
        if y < 3.5:
            target_angle = 0.0
            target_vx = 0.0 if y < 2.5 else target_vx
        torque = 1000.0 * (target_angle - angle) - 250.0 * omega
        torque = max(-120.0, min(120.0, torque))
        sandbox.apply_thrust(thrust, torque)

def build_agent_Stage_3(sandbox): return Stage3LanderAgent(sandbox.get_lander_body())

def agent_action_Stage_3(sandbox, agent, step_count): agent.act(sandbox, step_count)

class Stage4LanderAgent(BaselineLanderAgent):
    def act(self, sandbox, step_count):
        delay_t = 0.133
        pos = self.agent_body.position
        vel = self.agent_body.linearVelocity
        x, y = pos.x, pos.y
        vx, vy = vel.x, vel.y
        angle = self.agent_body.angle
        omega = self.agent_body.angularVelocity
        x_pred = x + vx * delay_t
        y_pred = y + vy * delay_t - 0.5 * 10.0 * (delay_t**2)
        vx_pred = vx
        vy_pred = vy - 10.0 * delay_t
        angle_pred = angle + omega * delay_t
        g = 10.0 if step_count < 150 else 11.5
        hover_thrust = 50.0 * g
        t_pred = (step_count + 8) * self.DT
        plat_x_pred = 17.0 + 1.8 * math.sin(2.0 * math.pi * t_pred / 6.0)
        if x_pred < 16.0:
            target_x, target_y = 16.5, 13.0
            target_vx = 3.5
        else:
            target_x = max(15.5, plat_x_pred)
            target_y = 1.05
            target_vx = 1.2 * (target_x - x_pred)
        target_vy = 1.2 * (target_y - y_pred)
        if y_pred < 5.0:
            target_vy = max(-0.8, min(0.8, target_vy))
        else:
            target_vy = max(-2.5, min(2.5, target_vy))
        thrust = hover_thrust + 1000.0 * (target_vy - vy_pred)
        thrust /= max(0.8, math.cos(angle_pred))
        thrust = max(0.0, min(600.0, thrust))
        target_angle = -0.2 * (target_vx - vx_pred)
        target_angle = max(-0.4, min(0.4, target_angle))
        if y_pred < 4.5:
            target_angle = 0.0
            target_vx = 0.0 if y_pred < 3.0 else target_vx
        torque = 800.0 * (target_angle - angle_pred) - 200.0 * omega
        torque = max(-120.0, min(120.0, torque))
        sandbox.apply_thrust(thrust, torque)

def build_agent_Stage_4(sandbox): return Stage4LanderAgent(sandbox.get_lander_body())

def agent_action_Stage_4(sandbox, agent, step_count): agent.act(sandbox, step_count)
