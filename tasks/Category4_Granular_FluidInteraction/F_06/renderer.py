"""
F-06: The Pipeline task rendering module
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class F06Renderer(Renderer):
    """F-06: The Pipeline task specific renderer"""

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        # Enforce 16:9 aspect ratio and 1280x720 resolution
        if self.simulator.screen_width != 1280 or self.simulator.screen_height != 720:
            self.simulator.screen_width = 1280
            self.simulator.screen_height = 720
            if self.simulator.can_display:
                import pygame
                self.simulator.screen = pygame.Surface((1280, 720))

        # Panoramic viewport: fix PPM and offset to see the entire relevant area
        # 1280 / 28 = 45.7 PPM captures the full 26m width with margin
        self.simulator.ppm = 45
        # Center camera on x=13 (middle of 26m floor)
        # 640 = 13 * 45 - offset_x => offset_x = 585 - 640 = -55
        self.set_camera_offset(-55, 0)

        self.clear((0, 0, 0))  # Background: Pure Black

        # Academic Colors
        COLOR_ENVIRONMENT = (230, 194, 41)   # #E6C229: Goldenrod Yellow
        COLOR_STRUCTURE = (76, 175, 80)      # #4CAF50: Material Green
        COLOR_FLUID = (100, 160, 220)        # Professional Blue
        COLOR_PIT = (200, 80, 80)            # Muted Red for danger zones

        for body in sandbox.world.bodies:
            if body.type == staticBody:
                self.draw_body(
                    body,
                    dynamic_color=COLOR_ENVIRONMENT,
                    static_color=COLOR_ENVIRONMENT,
                    outline_color=(140, 130, 110),
                    outline_width=2,
                )

        if hasattr(sandbox, "_fluid_particles"):
            default_radius = getattr(sandbox, "_PARTICLE_RADIUS", 0.10)
            for p in sandbox._fluid_particles:
                if p is not None and p.active:
                    px, py = p.position.x, p.position.y
                    r = default_radius
                    for f in p.fixtures:
                        if hasattr(f.shape, "radius"):
                            r = f.shape.radius
                            break
                    self.draw_circle(px, py, r, COLOR_FLUID, outline_color=(130, 190, 255), outline_width=1)

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

        # Pits (Loss zones)
        for pit_attr in ["PIT", "PIT2", "PIT3"]:
            if hasattr(sandbox, f"{pit_attr}_X_MIN"):
                px1 = getattr(sandbox, f"{pit_attr}_X_MIN")
                px2 = getattr(sandbox, f"{pit_attr}_X_MAX")
                py1 = getattr(sandbox, f"{pit_attr}_Y_MIN")
                py2 = getattr(sandbox, f"{pit_attr}_Y_MAX")
                self.draw_line(px1, py1, px2, py1, COLOR_PIT, 2)
                self.draw_line(px2, py1, px2, py2, COLOR_PIT, 2)
                self.draw_line(px2, py2, px1, py2, COLOR_PIT, 2)
                self.draw_line(px1, py2, px1, py1, COLOR_PIT, 2)

        # Headwind threshold (Academic Blue-Grey)
        if hasattr(sandbox, "HEADWIND_Y_THRESHOLD"):
            y_thresh = sandbox.HEADWIND_Y_THRESHOLD
            self.draw_line(0, y_thresh, 26, y_thresh, (100, 130, 180), 1)

        # Gravity well (Muted Purple)
        if hasattr(sandbox, "GRAVWELL_X_MIN"):
            gx1, gx2 = sandbox.GRAVWELL_X_MIN, sandbox.GRAVWELL_X_MAX
            gy1, gy2 = sandbox.GRAVWELL_Y_MIN, sandbox.GRAVWELL_Y_MAX
            self.draw_line(gx1, gy1, gx2, gy1, (150, 120, 180), 1)
            self.draw_line(gx2, gy1, gx2, gy2, (150, 120, 180), 1)
            self.draw_line(gx2, gy2, gx1, gy2, (150, 120, 180), 1)
            self.draw_line(gx1, gy2, gx1, gy1, (150, 120, 180), 1)