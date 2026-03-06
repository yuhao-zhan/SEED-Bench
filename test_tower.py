import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from tasks.Category4_Granular_FluidInteraction.F_03.environment import Sandbox
sandbox = Sandbox()

# 1. Base at origin
base1 = sandbox.add_anchored_base(-2.0, 0.0, 0.4, 1.5, angle=0)

# 2. Tower middle
tower2 = sandbox.add_beam(-2.0, 1.5, 0.4, 1.5)
sandbox.add_joint(base1, tower2, (-2.0, 0.75))

# 3. Tower top
tower3 = sandbox.add_beam(-2.0, 3.0, 0.4, 1.5)
sandbox.add_joint(tower2, tower3, (-2.0, 2.25))

# Now we have a tower up to y = 3.75!
# Let's attach an arm at y = 3.5.
# Arm is made of multiple segments welded together to reach length 4.5.
arm1 = sandbox.add_beam(-2.0 + 0.75, 3.5, 1.5, 0.2)
arm2 = sandbox.add_beam(-2.0 + 1.5 + 0.75, 3.5, 1.5, 0.2)
arm3 = sandbox.add_beam(-2.0 + 3.0 + 0.75, 3.5, 1.5, 0.2)

sandbox.add_joint(arm1, arm2, (-2.0 + 1.5, 3.5))
sandbox.add_joint(arm2, arm3, (-2.0 + 3.0, 3.5))

# Revolute joint to tower
joint1 = sandbox.add_revolute_joint(tower3, arm1, (-2.0, 3.5), enable_motor=True, max_motor_torque=90000.0)

for step in range(30):
    joint1.motorSpeed = -2.0
    sandbox.step(1/60.0)
    print(f"step {step} arm1 angle {joint1.angle:.2f}, y {arm1.position.y:.2f}, arm3 y {arm3.position.y:.2f}")
