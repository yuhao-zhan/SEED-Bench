#!/usr/bin/env python3
"""
Generate initial_environment.gif for K-03: The Gripper
Shows the environment without any agent solution
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from common.simulator import Simulator, TIME_STEP
from environment import Sandbox
from renderer import K03Renderer


def generate_initial_gif():
    """Generate initial environment GIF"""
    print("Generating initial_environment.gif for K-03: The Gripper...")
    
    # Initialize simulator
    simulator = Simulator()
    can_display = simulator.init_display(headless=True, save_gif=True)
    
    if not can_display:
        print("Error: Cannot initialize display for GIF generation")
        return False
    
    # Initialize environment (no agent solution)
    environment = Sandbox()
    print("Environment initialized")
    
    # Initialize renderer
    renderer = K03Renderer(simulator)
    print("Renderer initialized")
    
    # Camera tracking (center on starting position)
    camera_offset_x = 0
    target_x = 6.0  # Target height for visualization
    
    # Run simulation for a few seconds to show environment
    max_steps = 300  # 5 seconds at 60 FPS
    frame_interval = 2  # Collect every 2 frames for smoother animation
    
    print(f"Running simulation for {max_steps} steps...")
    
    for step_count in range(max_steps):
        # Render frame
        renderer.render(environment, None, target_x, camera_offset_x)
        simulator.collect_frame(step_count, frame_interval=frame_interval)
        
        # Step physics (even without agent, let template fall/settle)
        environment.step(TIME_STEP)
    
    # Save GIF
    gif_path = os.path.join(os.path.dirname(__file__), 'initial_environment.gif')
    success = simulator.save_gif_animation(gif_path, duration=50)  # 50ms per frame
    
    # Cleanup
    simulator.quit()
    
    if success:
        print(f"✅ Initial environment GIF saved: {gif_path}")
    else:
        print(f"❌ Failed to save GIF")
    
    return success


if __name__ == "__main__":
    generate_initial_gif()
