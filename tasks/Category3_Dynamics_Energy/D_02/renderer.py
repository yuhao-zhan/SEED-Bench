"""
D-02: The Jumper task rendering module
Renders left platform, pit, right platform, build zone, jumper, and launcher.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class D02Renderer(Renderer):
    """D-02: The Jumper task renderer."""

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        # Enforce 16:9 aspect ratio
        if self.simulator.screen_width != 800 or self.simulator.screen_height != 450:
            self.simulator.screen_width = 800
            self.simulator.screen_height = 450
            if self.simulator.can_display:
                import pygame
                self.simulator.screen = pygame.Surface((800, 450))

        # Dynamic Camera Viewport based on terrain bounds
        bounds = sandbox.get_terrain_bounds()
        left_end = bounds.get("left_platform_end_x", 8.0)
        pit_w = bounds.get("pit_width", 18.0)
        right_start = bounds.get("right_platform_start_x", 26.0)
        # Assume right platform is 15m wide as in environment.py
        total_width = right_start + 15.0
        
        self.simulator.ppm = 17.0
        center_x_world = total_width / 2.0
        # Vertically center around the middle of the slot/platform range (0 to 15m)
        center_y_world = 8.5
        
        cam_x = center_x_world * self.simulator.ppm - self.simulator.screen_width / 2
        cam_y = self.simulator.screen_height / 2 - center_y_world * self.simulator.ppm
        self.set_camera_offset(cam_x, cam_y)
        
        self.clear((0, 0, 0))  # Pure Black

        # Academic Color Palette
        ENV_COLOR = (230, 194, 41)       # #E6C229 (Goldenrod Yellow)
        ENV_OUTLINE = (180, 144, 0)      # Darker Goldenrod
        BARRIER_COLOR = (220, 53, 69)    # #DC3545 (Material Red)
        BARRIER_OUTLINE = (150, 30, 40)  # Darker Red
        AGENT_COLOR = (76, 175, 80)      # #4CAF50 (Material Green)
        AGENT_OUTLINE = (26, 125, 30)    # Darker Green

        # Draw all bodies
        jumper_body = sandbox.get_jumper()
        for body in sandbox.world.bodies:
            is_environment = False
            is_barrier = False
            if hasattr(sandbox, "_terrain_bodies") and body in sandbox._terrain_bodies.values():
                is_environment = True
                # Identify if this specific body is a barrier or ceiling
                for key, val in sandbox._terrain_bodies.items():
                    if body == val and ("barrier" in key or "ceiling" in key):
                        is_barrier = True
                        break
            elif body == jumper_body:
                is_environment = True
            
            if is_barrier:
                self.draw_body(body,
                             dynamic_color=BARRIER_COLOR,
                             static_color=BARRIER_COLOR,
                             outline_color=BARRIER_OUTLINE,
                             outline_width=2)
            elif is_environment:
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

