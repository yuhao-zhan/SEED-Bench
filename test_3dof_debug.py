import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from tasks.Category4_Granular_FluidInteraction.F_03.environment import Sandbox
sandbox = Sandbox()
base = sandbox.add_anchored_base(-2.0, 0.0, 0.4, 0.2, angle=0)

shoulder_len = 3.0
shoulder = sandbox.add_beam(-2.0, 1.5, 0.2, shoulder_len, angle=0)
joint1 = sandbox.add_revolute_joint(base, shoulder, (-2.0, 0.0), enable_motor=True, max_motor_torque=900000.0)

for step in range(120):
    joint1.motorSpeed = -5.0
    sandbox.step(1/60.0)
    if step % 20 == 0:
        print(f"step {step} angle {joint1.angle:.2f}")

