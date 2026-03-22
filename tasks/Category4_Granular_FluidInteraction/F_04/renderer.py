"""
F-04: The Filter task rendering module (Three-way: small / medium / large)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class F04Renderer(Renderer):
    """F-04: The Filter task specific renderer (three-way separation)"""

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        # Enforce 16:9 aspect ratio and 1280x720 resolution
        if self.simulator.screen_width != 1280 or self.simulator.screen_height != 720:
            self.simulator.screen_width = 1280
            self.simulator.screen_height = 720
            if self.simulator.can_display:
                import pygame
                self.simulator.screen = pygame.Surface((1280, 720))

        # Panoramic viewport: fix PPM and offset to see the entire relevant area
        floor_w = float(getattr(sandbox, "FLOOR_LENGTH", 16.0))
        # 1280 / 20 = 64 PPM captures the full floor width with margin when floor_w ≈ 16 m
        self.simulator.ppm = 64
        # Center camera on x=8 (middle of floor)
        # 640 = 8 * 64 - offset_x => offset_x = 512 - 640 = -128
        self.set_camera_offset(-128, 0)
        
        self.clear((0, 0, 0))  # Background: Pure Black

        # Academic Colors
        COLOR_ENVIRONMENT = (230, 194, 41)   # #E6C229: Goldenrod Yellow
        COLOR_STRUCTURE = (76, 175, 80)      # #4CAF50: Material Green
        
        # Particle Colors
        COLOR_SMALL = (120, 180, 220)        # Light Blue
        COLOR_MEDIUM = (120, 220, 120)       # Light Green
        COLOR_LARGE = (220, 140, 100)        # Light Orange/Red

        agent_bodies = set(getattr(sandbox, "_bodies", []) or [])
        for body in sandbox.world.bodies:
            if body.type == staticBody and body in agent_bodies:
                continue
            if body.type == staticBody:
                self.draw_body(
                    body,
                    dynamic_color=COLOR_ENVIRONMENT,
                    static_color=COLOR_ENVIRONMENT,
                    outline_color=(140, 130, 110),
                    outline_width=2,
                )

        if hasattr(sandbox, "_particles_small"):
            for p in sandbox._particles_small:
                if p is not None and p.active:
                    px, py = p.position.x, p.position.y
                    r = 0.06
                    for f in p.fixtures:
                        if hasattr(f.shape, "radius"):
                            r = f.shape.radius
                            break
                    self.draw_circle(px, py, r, COLOR_SMALL, outline_color=(150, 200, 255), outline_width=1)

        if hasattr(sandbox, "_particles_medium"):
            for p in sandbox._particles_medium:
                if p is not None and p.active:
                    px, py = p.position.x, p.position.y
                    r = 0.10
                    for f in p.fixtures:
                        if hasattr(f.shape, "radius"):
                            r = f.shape.radius
                            break
                    self.draw_circle(px, py, r, COLOR_MEDIUM, outline_color=(150, 255, 150), outline_width=1)

        if hasattr(sandbox, "_particles_large"):
            for p in sandbox._particles_large:
                if p is not None and p.active:
                    px, py = p.position.x, p.position.y
                    r = 0.14
                    for f in p.fixtures:
                        if hasattr(f.shape, "radius"):
                            r = f.shape.radius
                            break
                    self.draw_circle(px, py, r, COLOR_LARGE, outline_color=(255, 180, 130), outline_width=1)

        for body in sandbox._bodies:
            if body.active:
                self.draw_body(
                    body,
                    dynamic_color=COLOR_STRUCTURE,
                    static_color=COLOR_STRUCTURE,
                    outline_color=(50, 150, 50),
                    outline_width=2,
                )

        # Draw zone boundaries (Goldenrod Yellow). Small-zone ceiling and medium-zone floor share y — draw once.
        if hasattr(sandbox, "SMALL_ZONE_Y_MAX"):
            self.draw_line(0, sandbox.SMALL_ZONE_Y_MAX, floor_w, sandbox.SMALL_ZONE_Y_MAX, COLOR_ENVIRONMENT, 1)
        if hasattr(sandbox, "MEDIUM_ZONE_Y_MIN"):
            y_mid = sandbox.MEDIUM_ZONE_Y_MIN
            if not hasattr(sandbox, "SMALL_ZONE_Y_MAX") or abs(y_mid - sandbox.SMALL_ZONE_Y_MAX) > 1e-6:
                self.draw_line(0, y_mid, floor_w, y_mid, COLOR_ENVIRONMENT, 1)
        if hasattr(sandbox, "LARGE_ZONE_Y_MIN"):
            self.draw_line(0, sandbox.LARGE_ZONE_Y_MIN, floor_w, sandbox.LARGE_ZONE_Y_MIN, COLOR_ENVIRONMENT, 1)

        if hasattr(sandbox, "BUILD_ZONE_X_MIN"):
            x_min = sandbox.BUILD_ZONE_X_MIN
            x_max = sandbox.BUILD_ZONE_X_MAX
            y_min = sandbox.BUILD_ZONE_Y_MIN
            y_max = sandbox.BUILD_ZONE_Y_MAX
            self.draw_line(x_min, y_min, x_max, y_min, COLOR_ENVIRONMENT, 1)
            self.draw_line(x_max, y_min, x_max, y_max, COLOR_ENVIRONMENT, 1)
            self.draw_line(x_max, y_max, x_min, y_max, COLOR_ENVIRONMENT, 1)
            self.draw_line(x_min, y_max, x_min, y_min, COLOR_ENVIRONMENT, 1)
