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
        self.set_camera_offset(camera_offset_x)
        self.clear((30, 30, 30))  # Dark background consistent with other categories

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
                        dynamic_color=(70, 130, 180),
                        static_color=(50, 110, 160),
                        outline_color=(90, 150, 200),
                        outline_width=2,
                    )
                else:
                    self.draw_body(
                        body,
                        dynamic_color=(100, 150, 240),
                        static_color=(95, 90, 75),
                        outline_color=(140, 130, 110),
                        outline_width=2,
                    )

        boat = sandbox._terrain_bodies.get("boat")
        if boat and boat.active:
            self.draw_body(
                boat,
                dynamic_color=(140, 100, 60),
                static_color=(140, 100, 60),
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
                    self.draw_circle(cx, cy, r, (200, 160, 100), outline_color=(230, 190, 120), outline_width=1)

        for body in sandbox._bodies:
            if body.active:
                self.draw_body(
                    body,
                    dynamic_color=(100, 140, 100),
                    static_color=(100, 140, 100),
                    outline_color=(70, 100, 70),
                    outline_width=2,
                )

        if hasattr(sandbox, "CARGO_WATER_Y"):
            self.draw_line(5, sandbox.CARGO_WATER_Y, 25, sandbox.CARGO_WATER_Y, (255, 100, 100), 1)

        if hasattr(sandbox, "BUILD_ZONE_X_MIN"):
            x_min = sandbox.BUILD_ZONE_X_MIN
            x_max = sandbox.BUILD_ZONE_X_MAX
            y_min = sandbox.BUILD_ZONE_Y_MIN
            y_max = sandbox.BUILD_ZONE_Y_MAX
            self.draw_line(x_min, y_min, x_max, y_min, (255, 255, 0), 1)
            self.draw_line(x_max, y_min, x_max, y_max, (255, 255, 0), 1)
            self.draw_line(x_max, y_max, x_min, y_max, (255, 255, 0), 1)
            self.draw_line(x_min, y_max, x_min, y_min, (255, 255, 0), 1)
