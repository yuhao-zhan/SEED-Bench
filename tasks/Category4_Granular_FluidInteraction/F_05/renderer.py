"""
F-05: The Boat task rendering module
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class F05Renderer(Renderer):
    """F-05: The Boat task specific renderer"""

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        # Enforce 16:9 aspect ratio and 1280x720 resolution
        if self.simulator.screen_width != 1280 or self.simulator.screen_height != 720:
            self.simulator.screen_width = 1280
            self.simulator.screen_height = 720
            if self.simulator.can_display:
                import pygame
                self.simulator.screen = pygame.Surface((1280, 720))

        # Panoramic viewport: fix PPM and offset to see the entire relevant area
        # 1280 / 32 = 40 PPM captures the full 30m width with margin
        self.simulator.ppm = 40
        # Center camera on x=15 (middle of 30m floor)
        # 640 = 15 * 40 - offset_x => offset_x = 600 - 640 = -40
        self.set_camera_offset(-40, 0)
        
        self.clear((0, 0, 0))  # Background: Pure Black

        # Academic Colors
        COLOR_ENVIRONMENT = (230, 194, 41)   # #E6C229: Goldenrod Yellow
        COLOR_STRUCTURE = (76, 175, 80)      # #4CAF50: Material Green
        COLOR_WATER = (70, 130, 180)         # Professional Steel Blue
        COLOR_WATER_OUTLINE = (100, 160, 220)
        COLOR_CARGO = (180, 140, 80)         # Academic Tan/Wood

        for body in sandbox.world.bodies:
            if body.type == staticBody:
                is_water = False
                for fixture in body.fixtures:
                    if getattr(fixture, 'isSensor', False):
                        is_water = True
                        break
                if is_water:
                    self.draw_body(
                        body,
                        dynamic_color=COLOR_WATER,
                        static_color=COLOR_WATER,
                        outline_color=COLOR_WATER_OUTLINE,
                        outline_width=2,
                    )
                else:
                    self.draw_body(
                        body,
                        dynamic_color=COLOR_ENVIRONMENT,
                        static_color=COLOR_ENVIRONMENT,
                        outline_color=(140, 130, 110),
                        outline_width=2,
                    )

        boat = sandbox._terrain_bodies.get("boat")
        if boat and boat.active:
            self.draw_body(
                boat,
                dynamic_color=COLOR_ENVIRONMENT,
                static_color=COLOR_ENVIRONMENT,
                outline_color=(180, 130, 80),
                outline_width=2,
            )

        if hasattr(sandbox, "_cargo"):
            for c in sandbox._cargo:
                if c is not None and c.active:
                    cx, cy = c.position.x, c.position.y
                    r = 0.15
                    for f in c.fixtures:
                        if hasattr(f.shape, "radius"):
                            r = f.shape.radius
                            break
                    self.draw_circle(cx, cy, r, COLOR_CARGO, outline_color=(230, 190, 120), outline_width=1)

        for body in sandbox._bodies:
            if body.active:
                self.draw_body(
                    body,
                    dynamic_color=COLOR_STRUCTURE,
                    static_color=COLOR_STRUCTURE,
                    outline_color=(70, 100, 70),
                    outline_width=2,
                )

        if hasattr(sandbox, "CARGO_WATER_Y"):
            self.draw_line(5, sandbox.CARGO_WATER_Y, 25, sandbox.CARGO_WATER_Y, COLOR_ENVIRONMENT, 1)

        if hasattr(sandbox, "BUILD_ZONE_X_MIN"):
            x_min = sandbox.BUILD_ZONE_X_MIN
            x_max = sandbox.BUILD_ZONE_X_MAX
            y_min = sandbox.BUILD_ZONE_Y_MIN
            y_max = sandbox.BUILD_ZONE_Y_MAX
            self.draw_line(x_min, y_min, x_max, y_min, COLOR_ENVIRONMENT, 1)
            self.draw_line(x_max, y_min, x_max, y_max, COLOR_ENVIRONMENT, 1)
            self.draw_line(x_max, y_max, x_min, y_max, COLOR_ENVIRONMENT, 1)
            self.draw_line(x_min, y_max, x_min, y_min, COLOR_ENVIRONMENT, 1)
