import sys
sys.path.insert(0, '.')
from tasks.Category5_Cybernetics_Control.C_02.environment import Sandbox
from tasks.Category5_Cybernetics_Control.C_02.agent import LanderAgent

s = Sandbox()
agent = LanderAgent(s.get_lander_body())

for step in range(1, 1000):
    agent.act(s, step)
    s.step(1/60.0)
    pos = s.get_lander_position()
    v = s._get_lander_velocity()
    t = s._thrust_queue[-1][0] if s._thrust_queue else 0
    if step % 20 == 0 or pos[1] < 2.0:
        print(f"step {step:3d}: x={pos[0]:.2f}, y={pos[1]:.2f}, vx={v[0]:.2f}, vy={v[1]:.2f}, thrust_cmd={t:.1f}, angle={s.get_lander_angle():.2f}")
    if pos[1] <= 1.5:
        print("Landed!")
        break
