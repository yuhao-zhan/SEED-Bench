"""
D-05: The Hammer task rendering module
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class D05Renderer(Renderer):
    """D-05: The Hammer task renderer."""

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        # Enforce 16:9 aspect ratio
        if self.simulator.screen_width != 800 or self.simulator.screen_height != 450:
            self.simulator.screen_width = 800
            self.simulator.screen_height = 450
            if self.simulator.can_display:
                import pygame
                self.simulator.screen = pygame.Surface((800, 450))

        # Panoramic Camera Viewport
        self.simulator.ppm = 40.0
        center_x_world = 10.0
        center_y_world = 5.5
        
        cam_x = center_x_world * self.simulator.ppm - self.simulator.screen_width / 2
        cam_y = self.simulator.screen_height / 2 - center_y_world * self.simulator.ppm
        self.set_camera_offset(cam_x, cam_y)
        
        self.clear((0, 0, 0))  # Pure Black

        # Academic Color Palette
        ENV_COLOR = (230, 194, 41)       # #E6C229 (Goldenrod Yellow)
        ENV_OUTLINE = (180, 144, 0)      # Darker Goldenrod
        AGENT_COLOR = (76, 175, 80)      # #4CAF50 (Material Green)
        AGENT_OUTLINE = (26, 125, 30)    # Darker Green

        # Draw all bodies
        shell = sandbox._terrain_bodies.get("shell")
        shield = sandbox._terrain_bodies.get("shield")
        pendulum_rod = sandbox._terrain_bodies.get("pendulum_rod")
        pendulum_anchor = sandbox._terrain_bodies.get("pendulum_anchor")
        
        for body in sandbox.world.bodies:
            is_environment = False
            if hasattr(sandbox, "_terrain_bodies") and body in sandbox._terrain_bodies.values():
                is_environment = True
            elif body in (shell, shield, pendulum_rod, pendulum_anchor):
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

        # Build zone outline
        if hasattr(sandbox, "BUILD_ZONE_X_MIN"):
            x_min, x_max = sandbox.BUILD_ZONE_X_MIN, sandbox.BUILD_ZONE_X_MAX
            y_min, y_max = sandbox.BUILD_ZONE_Y_MIN, sandbox.BUILD_ZONE_Y_MAX
            self.draw_line(x_min, y_min, x_max, y_min, ENV_COLOR, 1)
            self.draw_line(x_max, y_min, x_max, y_max, ENV_COLOR, 1)
            self.draw_line(x_max, y_max, x_min, y_max, ENV_COLOR, 1)
            self.draw_line(x_min, y_max, x_min, y_min, ENV_COLOR, 1)

