"""
F-03: The Excavator — rendering module.
Pit x=[0,5], Hopper at (-5, 3), base at (-2, 0).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class F03Renderer(Renderer):
    """F-03: The Excavator renderer (pit, hopper, excavator)."""

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        # Enforce 16:9 aspect ratio and 1280x720 resolution
        if self.simulator.screen_width != 1280 or self.simulator.screen_height != 720:
            self.simulator.screen_width = 1280
            self.simulator.screen_height = 720
            if self.simulator.can_display:
                import pygame
                self.simulator.screen = pygame.Surface((1280, 720))

        # Panoramic viewport: fix PPM and offset to see the entire relevant area
        # 1280 / 24 = 53.3 PPM captures the full 20m floor width with margin
        self.simulator.ppm = 50
        # Center camera on x=0
        self.set_camera_offset(0, 0)
        # Recalculate camera offset to center world x=0 on screen x=640
        # screen_x = world_x * ppm - offset_x => 640 = 0 * 50 - offset_x => offset_x = -640
        self.set_camera_offset(-640, 0)
        
        self.clear((0, 0, 0))  # Background: Pure Black

        # Academic Colors
        COLOR_ENVIRONMENT = (230, 194, 41)   # #E6C229: Goldenrod Yellow
        COLOR_STRUCTURE = (76, 175, 80)      # #4CAF50: Material Green
        COLOR_SAND = (194, 178, 128)         # Ecru/Sand
        COLOR_SAND_SUCCESS = (100, 220, 100) # Green for particles in hopper

        for body in sandbox.world.bodies:
            if body.type == staticBody:
                self.draw_body(
                    body,
                    dynamic_color=COLOR_ENVIRONMENT,
                    static_color=COLOR_ENVIRONMENT,
                    outline_color=(140, 110, 80),
                    outline_width=2,
                )

        if hasattr(sandbox, "_particles"):
            for p in sandbox._particles:
                if p is not None and p.active:
                    px, py = p.position.x, p.position.y
                    r = 0.06
                    for f in p.fixtures:
                        if hasattr(f.shape, "radius"):
                            r = f.shape.radius
                            break
                    x_min = getattr(sandbox, "HOPPER_VALID_X_MIN", sandbox.HOPPER_X_MIN)
                    x_max = getattr(sandbox, "HOPPER_VALID_X_MAX", sandbox.HOPPER_X_MAX)
                    y_min = getattr(sandbox, "HOPPER_VALID_Y_MIN", sandbox.HOPPER_Y_MIN)
                    y_max = getattr(sandbox, "HOPPER_VALID_Y_MAX", sandbox.HOPPER_Y_MAX)
                    in_hopper = (
                        x_min <= px <= x_max
                        and y_min <= py <= y_max
                    )
                    if in_hopper:
                        self.draw_circle(px, py, r, COLOR_SAND_SUCCESS, outline_color=(140, 255, 140), outline_width=2)
                    else:
                        self.draw_circle(px, py, r, COLOR_SAND, outline_color=(200, 220, 120), outline_width=1)

        for body in sandbox._bodies:
            if body.active:
                self.draw_body(
                    body,
                    dynamic_color=COLOR_STRUCTURE,
                    static_color=COLOR_STRUCTURE,
                    outline_color=(50, 150, 50),
                    outline_width=2,
                )

        if hasattr(sandbox, "BUILD_ZONE_X_MIN"):
            x_min = sandbox.BUILD_ZONE_X_MIN
            x_max = sandbox.BUILD_ZONE_X_MAX
            y_min = sandbox.BUILD_ZONE_Y_MIN
            y_max = sandbox.BUILD_ZONE_Y_MAX
            self.draw_line(x_min, y_min, x_max, y_min, COLOR_ENVIRONMENT, 1)
            self.draw_line(x_max, y_min, x_max, y_max, COLOR_ENVIRONMENT, 1)
            self.draw_line(x_max, y_max, x_min, y_max, COLOR_ENVIRONMENT, 1)
            self.draw_line(x_min, y_max, x_min, y_min, COLOR_ENVIRONMENT, 1)
