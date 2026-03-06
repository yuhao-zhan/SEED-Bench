import sys
import os
import math
sys.path.insert(0, os.path.abspath('.'))

from tasks.Category4_Granular_FluidInteraction.F_03.environment import Sandbox
sandbox = Sandbox()

BASE_X = -2.0
BASE_Y = 0.0

base1 = sandbox.add_anchored_base(BASE_X, 0.5, 0.4, 1.5, angle=0, density=100.0)
base2 = sandbox.add_beam(BASE_X, 2.0, 0.4, 1.5, angle=0, density=100.0)
sandbox.add_joint(base1, base2, (BASE_X, 1.25))
base3 = sandbox.add_beam(BASE_X, 3.5, 0.4, 1.5, angle=0, density=100.0)
sandbox.add_joint(base2, base3, (BASE_X, 2.75))

arm1 = sandbox.add_beam(BASE_X + 0.75, 4.0, 1.5, 0.2, density=100.0)
arm2 = sandbox.add_beam(BASE_X + 2.25, 4.0, 1.5, 0.2, density=100.0)
arm3 = sandbox.add_beam(BASE_X + 3.75, 4.0, 1.5, 0.2, density=100.0)
arm4 = sandbox.add_beam(BASE_X + 5.25, 4.0, 1.5, 0.2, density=100.0)

sandbox.add_joint(arm1, arm2, (BASE_X + 1.5, 4.0))
sandbox.add_joint(arm2, arm3, (BASE_X + 3.0, 4.0))
sandbox.add_joint(arm3, arm4, (BASE_X + 4.5, 4.0))

arm_tip_x = BASE_X + 6.0
arm_tip_y = 4.0
scoop = sandbox.add_scoop(arm_tip_x, arm_tip_y, 0.65, 0.45, density=280.0)

_arm_joint = sandbox.add_revolute_joint(base3, arm1, (BASE_X, 4.0), enable_motor=True, max_motor_torque=90000.0)
_bucket_joint = sandbox.add_revolute_joint(arm4, scoop, (arm_tip_x, arm_tip_y), enable_motor=True, max_motor_torque=30000.0)

def sim(t_arm, t_bucket, steps):
    for _ in range(steps):
        _arm_joint.motorSpeed = 3.0 * (t_arm - _arm_joint.angle)
        _bucket_joint.motorSpeed = 5.0 * (t_bucket - scoop.angle)
        sandbox.step(1/60.0)
    print(f"arm: {_arm_joint.angle:.2f}, bucket: {scoop.angle:.2f}")
    print(f"scoop: {scoop.position.x:.2f}, {scoop.position.y:.2f}")

sim(-0.75, 0.2, 120)
sim(-0.75, -0.2, 60)
sim(2.1, -0.2, 120)
sim(2.1, 1.5, 60)
