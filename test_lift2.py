import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from tasks.Category4_Granular_FluidInteraction.F_03.environment import Sandbox

sandbox = Sandbox(terrain_config={"central_wall": False})
base = sandbox.add_anchored_base(-2.0, 0.0, 0.4, 0.2)
arm = sandbox.add_beam(0.0, 0.5, 4.0, 0.2)
joint = sandbox.add_revolute_joint(base, arm, (-2.0, 0.5), enable_motor=True, motor_speed=3.0, max_motor_torque=9000.0)

for step in range(60):
    sandbox.step(1/60.0)
print(f"final arm angle {joint.angle}")
