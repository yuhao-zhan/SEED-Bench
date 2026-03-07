"""
F-01: The Dam task rendering module
Renders terrain, water particles, dam structure, and build zone.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class F01Renderer(Renderer):
    """F-01: The Dam task specific renderer"""

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        # Enforce 16:9 aspect ratio and 1280x720 resolution
        if self.simulator.screen_width != 1280 or self.simulator.screen_height != 720:
            self.simulator.screen_width = 1280
            self.simulator.screen_height = 720
            if self.simulator.can_display:
                import pygame
                self.simulator.screen = pygame.Surface((1280, 720))

        # Panoramic viewport: fix PPM and offset to see the entire relevant area
        # 1280 / 40 = 32 PPM captures the full 40m floor width
        self.simulator.ppm = 32
        self.set_camera_offset(0, 0)
        
        self.clear((0, 0, 0))  # Background: Pure Black

        # Academic Colors
        COLOR_ENVIRONMENT = (230, 194, 41)   # #E6C229: Goldenrod Yellow
        COLOR_STRUCTURE = (76, 175, 80)      # #4CAF50: Material Green
        COLOR_WATER = (80, 140, 220)         # Professional Blue
        COLOR_WATER_OUTLINE = (120, 180, 255)

        # Draw static terrain (floor, left wall)
        for body in sandbox.world.bodies:
            if body.type == staticBody:
                self.draw_body(
                    body,
                    dynamic_color=COLOR_ENVIRONMENT,
                    static_color=COLOR_ENVIRONMENT,
                    outline_color=(180, 160, 120),
                    outline_width=2,
                )

        # Draw water particles (blue circles)
        if hasattr(sandbox, "_water_particles"):
            for particle in sandbox._water_particles:
                if particle is not None and particle.active:
                    px, py = particle.position.x, particle.position.y
                    radius = 0.12
                    for f in particle.fixtures:
                        if hasattr(f.shape, "radius"):
                            radius = f.shape.radius
                            break
                    self.draw_circle(px, py, radius, COLOR_WATER, outline_color=COLOR_WATER_OUTLINE, outline_width=1)

        # Draw dam structure (agent-built beams)
        for body in sandbox._bodies:
            if body.active:
                self.draw_body(
                    body,
                    dynamic_color=COLOR_STRUCTURE,
                    static_color=COLOR_STRUCTURE,
                    outline_color=(40, 120, 80),
                    outline_width=2,
                )

        # Draw downstream boundary line (Academic Yellow) at x = DOWNSTREAM_X_START
        if hasattr(sandbox, "DOWNSTREAM_X_START"):
            dx = sandbox.DOWNSTREAM_X_START
            self.draw_line(dx, 0, dx, 12, COLOR_ENVIRONMENT, 3)

        # Draw build zone outlines (Academic Yellow)
        for zone_name in ["left", "middle", "right"]:
            attr_min = f"BUILD_ZONE_{zone_name.upper()}_X_MIN"
            attr_max = f"BUILD_ZONE_{zone_name.upper()}_X_MAX"
            if hasattr(sandbox, attr_min):
                x_min = getattr(sandbox, attr_min)
                x_max = getattr(sandbox, attr_max)
                y_min = sandbox.BUILD_ZONE_Y_MIN
                y_max = sandbox.BUILD_ZONE_Y_MAX
                self.draw_line(x_min, y_min, x_max, y_min, COLOR_ENVIRONMENT, 1)
                self.draw_line(x_max, y_min, x_max, y_max, COLOR_ENVIRONMENT, 1)
                self.draw_line(x_max, y_max, x_min, y_max, COLOR_ENVIRONMENT, 1)
                self.draw_line(x_min, y_max, x_min, y_min, COLOR_ENVIRONMENT, 1)
