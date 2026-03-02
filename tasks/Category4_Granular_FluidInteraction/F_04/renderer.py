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
        self.set_camera_offset(camera_offset_x)
        self.clear((30, 30, 30))  # Dark background consistent with other categories

        for body in sandbox.world.bodies:
            if body.type == staticBody:
                self.draw_body(
                    body,
                    dynamic_color=(100, 150, 240),
                    static_color=(90, 85, 75),
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
                    self.draw_circle(px, py, r, (120, 180, 220), outline_color=(150, 200, 255), outline_width=1)

        if hasattr(sandbox, "_particles_medium"):
            for p in sandbox._particles_medium:
                if p is not None and p.active:
                    px, py = p.position.x, p.position.y
                    r = 0.10
                    for f in p.fixtures:
                        if hasattr(f.shape, "radius"):
                            r = f.shape.radius
                            break
                    self.draw_circle(px, py, r, (120, 220, 120), outline_color=(150, 255, 150), outline_width=1)

        if hasattr(sandbox, "_particles_large"):
            for p in sandbox._particles_large:
                if p is not None and p.active:
                    px, py = p.position.x, p.position.y
                    r = 0.14
                    for f in p.fixtures:
                        if hasattr(f.shape, "radius"):
                            r = f.shape.radius
                            break
                    self.draw_circle(px, py, r, (220, 140, 100), outline_color=(255, 180, 130), outline_width=1)

        for body in sandbox._bodies:
            if body.active:
                self.draw_body(
                    body,
                    dynamic_color=(100, 200, 100),  # Green dynamic objects
                    static_color=(100, 200, 100),
                    outline_color=(50, 150, 50),
                    outline_width=2,
                )

        if hasattr(sandbox, "SMALL_ZONE_Y_MAX"):
            self.draw_line(0, sandbox.SMALL_ZONE_Y_MAX, 16, sandbox.SMALL_ZONE_Y_MAX, (100, 200, 255), 1)
        if hasattr(sandbox, "MEDIUM_ZONE_Y_MIN"):
            self.draw_line(0, sandbox.MEDIUM_ZONE_Y_MIN, 16, sandbox.MEDIUM_ZONE_Y_MIN, (100, 255, 100), 1)
        if hasattr(sandbox, "LARGE_ZONE_Y_MIN"):
            self.draw_line(0, sandbox.LARGE_ZONE_Y_MIN, 16, sandbox.LARGE_ZONE_Y_MIN, (255, 180, 100), 1)

        if hasattr(sandbox, "BUILD_ZONE_X_MIN"):
            x_min = sandbox.BUILD_ZONE_X_MIN
            x_max = sandbox.BUILD_ZONE_X_MAX
            y_min = sandbox.BUILD_ZONE_Y_MIN
            y_max = sandbox.BUILD_ZONE_Y_MAX
            self.draw_line(x_min, y_min, x_max, y_min, (255, 255, 0), 1)
            self.draw_line(x_max, y_min, x_max, y_max, (255, 255, 0), 1)
            self.draw_line(x_max, y_max, x_min, y_max, (255, 255, 0), 1)
            self.draw_line(x_min, y_max, x_min, y_min, (255, 255, 0), 1)
