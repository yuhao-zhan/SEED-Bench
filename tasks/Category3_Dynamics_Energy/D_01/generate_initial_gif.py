#!/usr/bin/env python3
"""
Generate initial_environment.gif for D-01: The Launcher
Shows the environment without any agent solution (ground, build zone, projectile at rest, target zone).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.simulator import Simulator, TIME_STEP
from environment import Sandbox
from renderer import D01Renderer


def generate_initial_gif():
    """Generate initial environment GIF."""
    print("Generating initial_environment.gif for D-01: The Launcher...")

    simulator = Simulator()
    can_display = simulator.init_display(headless=True, save_gif=True)

    if not can_display:
        print("Error: Cannot initialize display for GIF generation")
        return False

    environment = Sandbox()
    print("Environment initialized")

    renderer = D01Renderer(simulator)
    print("Renderer initialized")

    # Camera: show both launch area and target zone (e.g. center at x=25)
    camera_offset_x = 0
    target_x = 42.5  # Center of target zone for reference

    max_steps = 300
    frame_interval = 2

    print(f"Running simulation for {max_steps} steps...")

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
