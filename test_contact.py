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
    if step == 100:
        for contact in sandbox._world.contacts:
            if contact.touching:
                fixA = contact.fixtureA
                fixB = contact.fixtureB
                bodyA = fixA.body
                bodyB = fixB.body
                
                # identify bodies
                def identify(b):
                    if b == base: return "base"
                    if b == shoulder: return "shoulder"
                    for k, v in sandbox._terrain_bodies.items():
                        if b == v: return f"terrain_{k}"
                    if b in sandbox._particles: return "particle"
                    return "unknown"
                
                print(f"Contact between {identify(bodyA)} and {identify(bodyB)}")
        print(f"shoulder pos: {shoulder.position}")
