"""
S-04: The Balancer task rendering module
Zoomed and centered so the pivot + beam + load fill the frame.
The 200kg load is drawn in a distinct color and the weld to the structure is shown so it doesn't look like it's floating.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody

# Zoom: smaller = camera further away
RENDER_SCALE = 1.2
# World position to place at screen center
CENTER_WORLD_X = 0.0
CENTER_WORLD_Y = 1.5

class S04Renderer(Renderer):
    """S-04: The Balancer task specific renderer — zoomed and centered."""

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        """Render scene with fixed camera: center on balancer and zoom in."""
        # Enforce 16:9 aspect ratio
        if self.simulator.screen_width != 800 or self.simulator.screen_height != 450:
            self.simulator.screen_width = 800
            self.simulator.screen_height = 450
            if self.simulator.can_display:
                import pygame
                self.simulator.screen = pygame.Surface((800, 450))
                
        # Panoramic Camera Viewport
        self.simulator.ppm = 30.0
        sw = self.simulator.screen_width
        sh = self.simulator.screen_height
        
        # Updated Academic Color palette
        ENV_COLOR = (230, 194, 41)       # #E6C229 (Goldenrod Yellow)
        ENV_OUTLINE = (180, 144, 0)      # Darker Goldenrod
        AGENT_COLOR = (76, 175, 80)      # #4CAF50 (Material Green)
        AGENT_OUTLINE = (26, 125, 30)    # Darker Green
        RED = (255, 0, 0)
        
        # Fix camera
        center_x_world = 1.5
        center_y_world = 2.0
        
        cam_x = center_x_world * self.simulator.ppm - sw / 2
        cam_y = sh / 2 - center_y_world * self.simulator.ppm
        self.set_camera_offset(cam_x, cam_y)
        self.clear((0, 0, 0))  # Pure Black background

        load_body = getattr(sandbox, "_terrain_bodies", {}).get("load")

        # Draw all bodies
        for body in sandbox.world.bodies:
            is_environment = False
            if hasattr(sandbox, '_terrain_bodies'):
                if body in sandbox._terrain_bodies.values():
                    is_environment = True
            
            if is_environment:
                self.draw_body(body,
                             dynamic_color=ENV_COLOR,
                             static_color=ENV_COLOR,
                             outline_color=ENV_OUTLINE,
                             outline_width=2)
            else:
                self.draw_body(body,
                             dynamic_color=AGENT_COLOR,
                             static_color=AGENT_COLOR,
                             outline_color=AGENT_OUTLINE,
                             outline_width=2)

        # Draw connection line from load to the structure (Red)
        if load_body is not None and getattr(sandbox, "_bodies", None):
            lx, ly = load_body.position.x, load_body.position.y
            best = None
            best_d = float("inf")
            for b in sandbox._bodies:
                if b is load_body:
                    continue
                d = (b.position.x - lx) ** 2 + (b.position.y - ly) ** 2
                if d < best_d:
                    best_d = d
                    best = b
            if best is not None:
                self.draw_line(best.position.x, best.position.y, lx, ly, RED, width=2)
