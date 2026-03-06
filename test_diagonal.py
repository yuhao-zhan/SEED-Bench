import sys
import os
import math
sys.path.insert(0, os.path.abspath('.'))

from tasks.Category4_Granular_FluidInteraction.F_03.environment import Sandbox
sandbox = Sandbox()

BASE_X = -2.0
BASE_Y = 0.0

# Base tower up to y=2.0
base1 = sandbox.add_anchored_base(BASE_X, 0.5, 0.4, 1.5, angle=0, density=100.0)
base2 = sandbox.add_beam(BASE_X, 1.75, 0.4, 1.0, angle=0, density=100.0)
sandbox.add_joint(base1, base2, (BASE_X, 1.25))

# Shoulder length 2.5, points right (angle 0)
shoulder = sandbox.add_beam(BASE_X + 1.25, 2.0, 2.5, 0.2, angle=0, density=100.0)
_shoulder_joint = sandbox.add_revolute_joint(base2, shoulder, (BASE_X, 2.0), enable_motor=True, max_motor_torque=90000.0)

# Forearm length 3.0, points UP and LEFT (angle 3*pi/4 = 2.35)
angle_f = 2.35
f_len = 3.0
f_cx = BASE_X + 2.5 + (f_len/2) * math.cos(angle_f)
f_cy = 2.0 + (f_len/2) * math.sin(angle_f)
forearm = sandbox.add_beam(f_cx, f_cy, f_len, 0.2, angle=angle_f, density=100.0)
_elbow_joint = sandbox.add_revolute_joint(shoulder, forearm, (BASE_X + 2.5, 2.0), enable_motor=True, max_motor_torque=90000.0)

# Scoop at tip
arm_tip_x = BASE_X + 2.5 + f_len * math.cos(angle_f)
arm_tip_y = 2.0 + f_len * math.sin(angle_f)
scoop = sandbox.add_scoop(arm_tip_x, arm_tip_y, 0.65, 0.45, angle=angle_f, density=280.0)
_bucket_joint = sandbox.add_revolute_joint(forearm, scoop, (arm_tip_x, arm_tip_y), enable_motor=True, max_motor_torque=30000.0)

# Print initial bounds
def print_bounds():
    for i, b in enumerate(sandbox._bodies):
        if not b.active: continue
        print(f"body {i} center {b.position.x:.2f}, {b.position.y:.2f}")

print("Initial bounds:")
print_bounds()

def sim(t_s, t_e, t_b, steps):
    for _ in range(steps):
        _shoulder_joint.motorSpeed = 3.0 * (t_s - _shoulder_joint.angle)
        _elbow_joint.motorSpeed = 3.0 * (t_e - _elbow_joint.angle)
        _bucket_joint.motorSpeed = 5.0 * (t_b - _bucket_joint.angle)
        sandbox.step(1/60.0)
    print(f"S: {_shoulder_joint.angle:.2f}, E: {_elbow_joint.angle:.2f}, B: {_bucket_joint.angle:.2f}")
    print(f"scoop: {scoop.position.x:.2f}, {scoop.position.y:.2f}")

print("--- PIT ---")
# unfold the arm to the pit
sim(-0.5, -2.0, -2.0, 120)
sim(-0.8, -2.5, -1.5, 120)
print("--- HOPPER ---")
sim(1.0, 0.0, 0.0, 120)
sim(2.0, -1.0, -1.0, 120)
sim(2.5, -2.0, -2.0, 60)
sim(2.5, -2.0, 1.0, 60) # dump
