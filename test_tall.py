import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from tasks.Category4_Granular_FluidInteraction.F_03.environment import Sandbox

sandbox = Sandbox()
# Base at x=-2, height 2.5, centered at y=1.25
base = sandbox.add_anchored_base(-2.0, 1.25, 0.4, 2.5, density=100.0)
arm_len = 5.5
arm = sandbox.add_beam(-2.0 + arm_len/2, 2.5, arm_len, 0.2, density=100.0)
joint = sandbox.add_revolute_joint(base, arm, (-2.0, 2.5), enable_motor=True, motor_speed=-1.0, max_motor_torque=90000.0)

for step in range(60):
    sandbox.step(1/60.0)
print(f"step {step}, arm angle {joint.angle:.3f}")
