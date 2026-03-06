import sys
import os
import math
sys.path.insert(0, os.path.abspath('.'))

from tasks.Category4_Granular_FluidInteraction.F_03.environment import Sandbox
sandbox = Sandbox()

BASE_X = -2.0
BASE_Y = 0.0

base1 = sandbox.add_anchored_base(BASE_X, 0.5, 0.4, 1.5, angle=0, density=100.0)
base2 = sandbox.add_beam(BASE_X, 1.75, 0.4, 1.0, angle=0, density=100.0)
sandbox.add_joint(base1, base2, (BASE_X, 1.25))

shoulder = sandbox.add_beam(BASE_X + 1.25, 2.0, 2.5, 0.2, angle=0, density=100.0)
_shoulder_joint = sandbox.add_revolute_joint(base2, shoulder, (BASE_X, 2.0), enable_motor=True, max_motor_torque=90000.0)

angle_f = 2.35
f_len = 3.0
f_cx = BASE_X + 2.5 + (f_len/2) * math.cos(angle_f)
f_cy = 2.0 + (f_len/2) * math.sin(angle_f)
forearm = sandbox.add_beam(f_cx, f_cy, f_len, 0.2, angle=angle_f, density=100.0)
_elbow_joint = sandbox.add_revolute_joint(shoulder, forearm, (BASE_X + 2.5, 2.0), enable_motor=True, max_motor_torque=90000.0)

arm_tip_x = BASE_X + 2.5 + f_len * math.cos(angle_f)
arm_tip_y = 2.0 + f_len * math.sin(angle_f)
scoop = sandbox.add_scoop(arm_tip_x, arm_tip_y, 0.65, 0.45, angle=angle_f, density=280.0)
_bucket_joint = sandbox.add_revolute_joint(forearm, scoop, (arm_tip_x, arm_tip_y), enable_motor=True, max_motor_torque=30000.0)

sandbox._shoulder_joint = _shoulder_joint
sandbox._elbow_joint = _elbow_joint
sandbox._bucket_joint = _bucket_joint

def agent_action(step_count):
    dt = 1.0 / 60.0
    t = step_count * dt
    phase_duration = 10.0
    phase = (t % phase_duration) / phase_duration
    
    s_ang = _shoulder_joint.angle
    e_ang = _elbow_joint.angle
    b_ang = _bucket_joint.angle
    
    if phase < 0.1:
        t_s, t_e, t_b = -0.5, -2.0, -2.0
    elif phase < 0.25:
        t_s, t_e, t_b = -0.8, -2.5, -1.5
    elif phase < 0.35:
        t_s, t_e, t_b = -0.5, -2.0, -0.5
    elif phase < 0.6:
        t_s, t_e, t_b = 1.0, 0.0, 0.0
    elif phase < 0.75:
        t_s, t_e, t_b = 1.8, -0.5, 0.0
    elif phase < 0.9:
        t_s, t_e, t_b = 1.8, -0.5, 1.5
    else:
        t_s, t_e, t_b = 0.0, 0.0, 0.0
        
    _shoulder_joint.motorSpeed = max(-4.0, min(4.0, 3.0 * (t_s - s_ang)))
    _elbow_joint.motorSpeed = max(-4.0, min(4.0, 3.0 * (t_e - e_ang)))
    _bucket_joint.motorSpeed = max(-5.0, min(5.0, 5.0 * (t_b - b_ang)))
    
    _shoulder_joint.motorEnabled = True
    _elbow_joint.motorEnabled = True
    _bucket_joint.motorEnabled = True

for step in range(600):
    agent_action(step)
    sandbox.step(1/60.0)
    
    if step % 60 == 0:
        print(f"step {step}, scoop pos {scoop.position.x:.2f}, {scoop.position.y:.2f} | Angles: {_shoulder_joint.angle:.2f}, {_elbow_joint.angle:.2f}, {_bucket_joint.angle:.2f}")

