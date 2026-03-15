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
        pos, vel = self.agent_body.position, self.agent_body.linearVelocity
        x, y, vx, vy = pos.x, pos.y, vel.x, vel.y
        angle, omega = self.agent_body.angle, self.agent_body.angularVelocity
        
        t_sim = step_count * self.DT
        t_p = t_sim + 0.1
        plat_x = 17.0 + 1.8 * math.sin(2.0 * math.pi * t_p / 6.0)
        plat_vx = (2.0 * math.pi * 1.8 / 6.0) * math.cos(2.0 * math.pi * t_p / 6.0)

        if x < 14.5:
            tx, ty = 15.5, 12.0
            tvx, tvy = 4.0, 0.0
        else:
            tx, ty = plat_x, 1.05
            tvx, tvy = plat_vx, -1.5
            if y < 4.0:
                tvy = -0.2

        g, m = 10.0, 50.0
        ay = 2.0 * (ty - y) + 5.0 * (tvy - vy)
        thrust = m * (g + ay)
        thrust /= max(0.5, math.cos(angle))
        thrust = max(0.0, min(600.0, thrust))

        ax = 1.0 * (tx - x) + 2.0 * (tvx - vx)
        target_angle = max(-0.5, min(0.5, -0.15 * ax))
        
        if y < 4.0: target_angle = 0.0
        
        torque = 1000.0 * (target_angle - angle) - 250.0 * omega
        torque = max(-120.0, min(120.0, torque))
        sandbox.apply_thrust(thrust, torque)

def build_agent(sandbox): return BaselineLanderAgent(sandbox.get_lander_body())
def agent_action(sandbox, agent, step_count): agent.act(sandbox, step_count)


class Stage1LanderAgent:
    def __init__(self, agent_body):
        self.agent_body = agent_body
        self.DT = 1.0 / 60.0

    @property
    def position(self): return self.agent_body.position
    @property
    def linearVelocity(self): return self.agent_body.linearVelocity

    def act(self, sandbox, step_count):
        pos, vel = self.agent_body.position, self.agent_body.linearVelocity
        x, y, vx, vy = pos.x, pos.y, vel.x, vel.y
        angle, omega = self.agent_body.angle, self.agent_body.angularVelocity
        
        t_sim = step_count * self.DT
        t_p = t_sim + 0.1
        plat_x = 17.0 + 1.8 * math.sin(2.0 * math.pi * t_p / 6.0)
        plat_vx = (2.0 * math.pi * 1.8 / 6.0) * math.cos(2.0 * math.pi * t_p / 6.0)

        if x < 13.5:
            tx, ty = 14.5, 12.0
            tvx, tvy = 4.0, 0.0
        else:
            tx, ty = plat_x, 1.05
            tvx, tvy = plat_vx, -2.0
            if y < 3.5:
                tvy = -0.4
                if y < 2.0:
                    tvy = -0.05

        g, m = 10.0, 50.0
        ay = 5.0 * (ty - y) + 15.0 * (tvy - vy)
        thrust = m * (g + ay)
        thrust /= max(0.5, math.cos(angle))
        thrust = max(0.0, min(600.0, thrust))

        ax = 1.5 * (tx - x) + 3.0 * (tvx - vx)
        target_angle = max(-0.4, min(0.4, -0.12 * ax))
        if y < 1.8: target_angle = 0.0
        
        torque = 1200.0 * (target_angle - angle) - 300.0 * omega
        torque = max(-120.0, min(120.0, torque))
        sandbox.apply_thrust(thrust, torque)

def build_agent_Stage_1(sandbox): return Stage1LanderAgent(sandbox.get_lander_body())
def agent_action_Stage_1(sandbox, agent, step_count): agent.act(sandbox, step_count)


class Stage2LanderAgent:
    def __init__(self, agent_body):
        self.agent_body = agent_body
        self.DT = 1.0 / 60.0
        self.delay_t = 12 * self.DT

    @property
    def position(self): return self.agent_body.position
    @property
    def linearVelocity(self): return self.agent_body.linearVelocity

    def act(self, sandbox, step_count):
        pos, vel = self.agent_body.position, self.agent_body.linearVelocity
        x, y, vx, vy = pos.x, pos.y, vel.x, vel.y
        angle, omega = self.agent_body.angle, self.agent_body.angularVelocity
        
        g = 10.0
        x_p = x + vx * self.delay_t
        y_p = y + vy * self.delay_t - 0.5 * g * self.delay_t**2
        vx_p = vx
        vy_p = vy - g * self.delay_t
        angle_p = angle + omega * self.delay_t

        t_target = (step_count + 12) * self.DT
        plat_x = 17.0 + 1.8 * math.sin(2.0 * math.pi * t_target / 6.0)
        plat_vx = (2.0 * math.pi * 1.8 / 6.0) * math.cos(2.0 * math.pi * t_target / 6.0)

        if x_p < 14.5:
            tx, ty = 15.5, 14.0 # Fly much higher
            tvx, tvy = 3.0, 0.0
        else:
            tx, ty = plat_x, 1.05
            tvx, tvy = plat_vx, -1.0
            if y_p < 4.5:
                tvy = -0.3

        m = 50.0
        ay = 4.0 * (ty - y_p) + 12.0 * (tvy - vy_p)
        thrust = m * (g + ay)
        thrust /= max(0.6, math.cos(angle_p))
        thrust = max(0.0, min(600.0, thrust))

        ax = 1.0 * (tx - x_p) + 4.0 * (tvx - vx_p)
        target_angle = max(-0.25, min(0.25, -0.1 * ax))
        if y_p < 4.0: target_angle = 0.0
        
        torque = 1000.0 * (target_angle - angle_p) - 300.0 * omega
        torque = max(-120.0, min(120.0, torque))
        sandbox.apply_thrust(thrust, torque)

def build_agent_Stage_2(sandbox): return Stage2LanderAgent(sandbox.get_lander_body())
def agent_action_Stage_2(sandbox, agent, step_count): agent.act(sandbox, step_count)


class Stage3LanderAgent:
    def __init__(self, agent_body):
        self.agent_body = agent_body
        self.DT = 1.0 / 60.0

    @property
    def position(self): return self.agent_body.position
    @property
    def linearVelocity(self): return self.agent_body.linearVelocity

    def act(self, sandbox, step_count):
        pos, vel = self.agent_body.position, self.agent_body.linearVelocity
        x, y, vx, vy = pos.x, pos.y, vel.x, vel.y
        angle, omega = self.agent_body.angle, self.agent_body.angularVelocity
        
        g = 10.0 if step_count < 150 else 18.0
        t_sim = step_count * self.DT
        t_p = t_sim + 0.1
        plat_x = 17.0 + 1.8 * math.sin(2.0 * math.pi * t_p / 6.0)
        plat_vx = (2.0 * math.pi * 1.8 / 6.0) * math.cos(2.0 * math.pi * t_p / 6.0)

        # Stage 3: Fuel is tight. Must be very aggressive.
        if x < 13.0:
            tx, ty = 14.0, 9.0
            tvx, tvy = 6.0, -1.0 # Start descending early
        else:
            tx, ty = plat_x, 1.05
            tvx, tvy = plat_vx, -4.0 # Fast drop
            if y < 3.5:
                tvy = -0.8
                if y < 1.8:
                    tvy = -0.3

        m = 50.0
        ay = 4.0 * (ty - y) + 12.0 * (tvy - vy)
        thrust = m * (g + ay)
        thrust /= max(0.5, math.cos(angle))
        thrust = max(0.0, min(1200.0, thrust))

        ax = 2.0 * (tx - x) + 4.0 * (tvx - vx)
        target_angle = max(-0.5, min(0.5, -0.15 * ax))
        if y < 2.5: target_angle = 0.0
        
        torque = 1500.0 * (target_angle - angle) - 400.0 * omega
        torque = max(-120.0, min(120.0, torque))
        sandbox.apply_thrust(thrust, torque)

def build_agent_Stage_3(sandbox): return Stage3LanderAgent(sandbox.get_lander_body())
def agent_action_Stage_3(sandbox, agent, step_count): agent.act(sandbox, step_count)


class Stage4LanderAgent:
    def __init__(self, agent_body):
        self.agent_body = agent_body
        self.DT = 1.0 / 60.0
        self.delay_t = 8 * self.DT

    @property
    def position(self): return self.agent_body.position
    @property
    def linearVelocity(self): return self.agent_body.linearVelocity

    def act(self, sandbox, step_count):
        pos, vel = self.agent_body.position, self.agent_body.linearVelocity
        x, y, vx, vy = pos.x, pos.y, vel.x, vel.y
        angle, omega = self.agent_body.angle, self.agent_body.angularVelocity
        
        g = 10.0 if step_count < 150 else 11.5
        x_p = x + vx * self.delay_t
        y_p = y + vy * self.delay_t - 0.5 * g * self.delay_t**2
        vx_p = vx
        vy_p = vy - g * self.delay_t
        angle_p = angle + omega * self.delay_t

        t_target = (step_count + 8) * self.DT
        plat_x = 17.0 + 1.8 * math.sin(2.0 * math.pi * t_target / 6.0)
        plat_vx = (2.0 * math.pi * 1.8 / 6.0) * math.cos(2.0 * math.pi * t_target / 6.0)

        if x_p < 14.0:
            tx, ty = 15.0, 11.0
            tvx, tvy = 4.0, 0.0
        else:
            tx, ty = plat_x, 1.05
            tvx, tvy = plat_vx, -2.0
            if y_p < 4.0:
                tvy = -0.5
                if y_p < 2.0:
                    tvy = -0.2

        m = 50.0
        ay = 5.0 * (ty - y_p) + 15.0 * (tvy - vy_p)
        thrust = m * (g + ay)
        thrust /= max(0.6, math.cos(angle_p))
        thrust = max(0.0, min(600.0, thrust))

        ax = 2.0 * (tx - x_p) + 5.0 * (tvx - vx_p)
        target_angle = max(-0.35, min(0.35, -0.15 * ax))
        if y_p < 3.0: target_angle = 0.0
        
        torque = 1500.0 * (target_angle - angle_p) - 400.0 * omega
        torque = max(-120.0, min(120.0, torque))
        sandbox.apply_thrust(thrust, torque)

def build_agent_Stage_4(sandbox): return Stage4LanderAgent(sandbox.get_lander_body())
def agent_action_Stage_4(sandbox, agent, step_count): agent.act(sandbox, step_count)
