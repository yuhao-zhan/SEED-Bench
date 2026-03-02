"""
F-02: The Amphibian task rendering module
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class F02Renderer(Renderer):
    """F-02: The Amphibian task specific renderer"""

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
                        dynamic_color=(80, 140, 200),
                        static_color=(60, 120, 180),
                        outline_color=(100, 160, 220),
                        outline_width=2,
                    )
                else:
                    self.draw_body(
                        body,
                        dynamic_color=(100, 150, 240),
                        static_color=(100, 90, 70),
                        outline_color=(160, 140, 110),
                        outline_width=2,
                    )

        for body in sandbox._bodies:
            if body.active:
                self.draw_body(
                    body,
                    dynamic_color=(100, 200, 100),  # Green dynamic objects
                    static_color=(100, 200, 100),
                    outline_color=(50, 150, 50),
                    outline_width=2,
                )

        if hasattr(sandbox, "TARGET_X"):
            tx = sandbox.TARGET_X
            self.draw_line(tx, 0, tx, 8, (255, 200, 80), 3)

        if hasattr(sandbox, "BUILD_ZONE_X_MIN"):
            x_min = sandbox.BUILD_ZONE_X_MIN
            x_max = sandbox.BUILD_ZONE_X_MAX
            y_min = sandbox.BUILD_ZONE_Y_MIN
            y_max = sandbox.BUILD_ZONE_Y_MAX
            self.draw_line(x_min, y_min, x_max, y_min, (255, 255, 0), 1)
            self.draw_line(x_max, y_min, x_max, y_max, (255, 255, 0), 1)
            self.draw_line(x_max, y_max, x_min, y_max, (255, 255, 0), 1)
            self.draw_line(x_min, y_max, x_min, y_min, (255, 255, 0), 1)
