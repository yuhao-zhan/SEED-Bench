import sys
import os
import math
sys.path.insert(0, os.path.abspath('.'))

from tasks.Category4_Granular_FluidInteraction.F_03.environment import Sandbox
sandbox = Sandbox()
base = sandbox.add_anchored_base(-2.0, 0.0, 0.4, 0.2, angle=0)

shoulder_len = 3.0
shoulder = sandbox.add_beam(-2.0, 1.5, 0.2, shoulder_len, angle=0) # vertical beam
joint1 = sandbox.add_revolute_joint(base, shoulder, (-2.0, 0.0), enable_motor=True, max_motor_torque=90000.0)

forearm_len = 4.0
forearm = sandbox.add_beam(-2.0 + forearm_len/2, 3.0, forearm_len, 0.2, angle=0)
joint2 = sandbox.add_revolute_joint(shoulder, forearm, (-2.0, 3.0), enable_motor=True, max_motor_torque=90000.0)

scoop = sandbox.add_scoop(-2.0 + forearm_len, 3.0, 0.65, 0.45, angle=0)
joint3 = sandbox.add_revolute_joint(forearm, scoop, (-2.0 + forearm_len, 3.0), enable_motor=True, max_motor_torque=90000.0)

def step_sim(t1, t2, t3, steps):
    for _ in range(steps):
        joint1.motorSpeed = 3.0 * (t1 - joint1.angle)
        joint2.motorSpeed = 3.0 * (t2 - joint2.angle)
        joint3.motorSpeed = 3.0 * (t3 - joint3.angle)
        sandbox.step(1/60.0)
    print(f"target: {t1:.2f}, {t2:.2f}, {t3:.2f} -> angles: {joint1.angle:.2f}, {joint2.angle:.2f}, {joint3.angle:.2f}")
    print(f"scoop pos: {scoop.position.x:.2f}, {scoop.position.y:.2f}")
    # print distance to central wall
    wall = sandbox._terrain_bodies.get("central_wall")
    if wall:
        print(f"Wall top: {wall.position.y + 1.5/2:.2f}")

step_sim(0.0, 0.0, 0.0, 60) # initial
print("--- PIT ---")
step_sim(-1.0, 0.5, 0.0, 120) 
step_sim(-1.2, 0.7, 0.2, 120)
print("--- HOPPER ---")
step_sim(0.0, 2.5, 0.0, 120)
step_sim(0.5, 2.8, -1.0, 120)
step_sim(0.5, 2.8, 1.5, 120) # Dump
