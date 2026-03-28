"""
D-03: Phase-Locked Gate — cart, rotating gate, build zone, target zone.
"""
import sys
import os
import pygame
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class D03Renderer(Renderer):
    """D-03: Phase-Locked Gate — cart, gate rod, build zone, target zone."""

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
        center_x_world = 8.0
        center_y_world = 4.5
        
        cam_x = center_x_world * self.simulator.ppm - self.simulator.screen_width / 2
        cam_y = self.simulator.screen_height / 2 - center_y_world * self.simulator.ppm
        self.set_camera_offset(cam_x, cam_y)
        
        self.clear((0, 0, 0))  # Pure Black

        # Academic Color Palette
        ENV_COLOR = (230, 194, 41)       # #E6C229 (Goldenrod Yellow)
        ENV_OUTLINE = (180, 144, 0)      # Darker Goldenrod
        AGENT_COLOR = (76, 175, 80)      # #4CAF50 (Material Green)
        AGENT_OUTLINE = (26, 125, 30)    # Darker Green

        # Draw environmental zones using ENV_COLOR
        # Target zone (x >= 11.75)
        tx = getattr(sandbox, "_target_x_min", 11.75)
        self.draw_line(tx, 0.4, tx, 4.0, ENV_COLOR, 3)
        self.draw_line(tx + 2, 0.4, tx + 2, 4.0, ENV_COLOR, 1)

        # Mud zone [5.5, 7.5] and Brake zone [12, 15]
        if hasattr(sandbox, "_mud_zone_x_min"):
            m1, m2 = sandbox._mud_zone_x_min, sandbox._mud_zone_x_max
            self.draw_line(m1, 0.4, m1, 4.0, ENV_COLOR, 1)
            self.draw_line(m2, 0.4, m2, 4.0, ENV_COLOR, 1)
        if hasattr(sandbox, "_brake_zone_x_min"):
            b1, b2 = sandbox._brake_zone_x_min, sandbox._brake_zone_x_max
            self.draw_line(b1, 0.4, b1, 4.0, ENV_COLOR, 1)
            self.draw_line(b2, 0.4, b2, 4.0, ENV_COLOR, 1)

        # Impulse zone [8, 9]
        if hasattr(sandbox, "_impulse_zone_x_min"):
            i1, i2 = sandbox._impulse_zone_x_min, sandbox._impulse_zone_x_max
            self.draw_line(i1, 0.4, i1, 4.0, ENV_COLOR, 1)
            self.draw_line(i2, 0.4, i2, 4.0, ENV_COLOR, 1)
        # Second impulse zone [10.5, 11]
        if hasattr(sandbox, "_impulse2_zone_x_min"):
            j1 = getattr(sandbox, "_impulse2_zone_x_min", 10.5)
            j2 = getattr(sandbox, "_impulse2_zone_x_max", 11.0)
            self.draw_line(j1, 0.4, j1, 4.0, ENV_COLOR, 2)
            self.draw_line(j2, 0.4, j2, 4.0, ENV_COLOR, 2)
        # Speed trap at x=9
        if hasattr(sandbox, "_speed_trap_x"):
            sx = getattr(sandbox, "_speed_trap_x", 9.0)
            self.draw_line(sx, 0.4, sx, 4.0, ENV_COLOR, 2)
        # Decel zone [9.5, 11]
        if hasattr(sandbox, "_decel_zone_x_min"):
            d1 = getattr(sandbox, "_decel_zone_x_min", 9.5)
            d2 = getattr(sandbox, "_decel_zone_x_max", 11.0)
            self.draw_line(d1, 0.4, d1, 4.0, ENV_COLOR, 2)
            self.draw_line(d2, 0.4, d2, 4.0, ENV_COLOR, 2)

        # Build zone outline
        if hasattr(sandbox, "BUILD_ZONE_X_MIN"):
            x_min, x_max = sandbox.BUILD_ZONE_X_MIN, sandbox.BUILD_ZONE_X_MAX
            y_min, y_max = sandbox.BUILD_ZONE_Y_MIN, sandbox.BUILD_ZONE_Y_MAX
            self.draw_line(x_min, y_min, x_max, y_min, ENV_COLOR, 1)
            self.draw_line(x_max, y_min, x_max, y_max, ENV_COLOR, 1)
            self.draw_line(x_max, y_max, x_min, y_max, ENV_COLOR, 1)
            self.draw_line(x_min, y_max, x_min, y_min, ENV_COLOR, 1)

        # Draw all bodies
        rod_bodies = [sandbox._terrain_bodies.get(k) for k in ("gate_rod", "gate_rod_2", "gate_rod_3", "gate_rod_4")]
        cabin = sandbox._terrain_bodies.get("vehicle_cabin")
        
        for body in sandbox.world.bodies:
            is_environment = False
            if hasattr(sandbox, "_terrain_bodies") and body in sandbox._terrain_bodies.values():
                is_environment = True
            elif body in rod_bodies or body == cabin:
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

