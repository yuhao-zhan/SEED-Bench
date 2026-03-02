#!/usr/bin/env python3
"""Generate initial_environment.gif for C-06: The Governor (no motor torque; wheel slows under load)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.simulator import Simulator, TIME_STEP
from environment import Sandbox
from renderer import C06Renderer


def generate_initial_gif():
    print("Generating initial_environment.gif for C-06: The Governor...")
    simulator = Simulator()
    can_display = simulator.init_display(headless=True, save_gif=True)
    if not can_display:
        print("Error: Cannot initialize display for GIF generation")
        return False
    environment = Sandbox()
    wheel = environment.get_wheel_body()
    if wheel is not None:
        wheel.angularVelocity = 3.0
    renderer = C06Renderer(simulator)
    camera_offset_x = 0
    target_x = 5.0
    max_steps = 400
    frame_interval = 2
    for step_count in range(max_steps):
        renderer.render(environment, None, target_x, camera_offset_x)
        simulator.collect_frame(step_count, frame_interval=frame_interval)
        environment.step(TIME_STEP)
    gif_path = os.path.join(os.path.dirname(__file__), "initial_environment.gif")
    success = simulator.save_gif_animation(gif_path, duration=50)
    simulator.quit()
    if success:
        print(f"Initial environment GIF saved: {gif_path}")
    else:
        print("Failed to save GIF")
    return success


if __name__ == "__main__":
    generate_initial_gif()
