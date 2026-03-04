"""
E-06: The Brownian task rendering module.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class E06Renderer(Renderer):
    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        self.set_camera_offset(camera_offset_x)
        self.clear((30, 30, 30))
        for body in sandbox.world.bodies:
            if body.type == staticBody:
                self.draw_body(body, dynamic_color=(100, 150, 240), static_color=(80, 90, 70),
                               outline_color=(120, 130, 100), outline_width=2)
        for body in sandbox.world.bodies:
            if body.type == dynamicBody:
                self.draw_body(body, dynamic_color=(100, 200, 100), static_color=(80, 90, 70),
                               outline_color=(50, 150, 50), outline_width=2)
        if hasattr(sandbox, "BUILD_ZONE_X_MIN"):
            x_min, x_max = sandbox.BUILD_ZONE_X_MIN, sandbox.BUILD_ZONE_X_MAX
            y_min, y_max = sandbox.BUILD_ZONE_Y_MIN, sandbox.BUILD_ZONE_Y_MAX
            self.draw_line(x_min, y_min, x_max, y_min, (255, 255, 0), 1)
            self.draw_line(x_max, y_min, x_max, y_max, (255, 255, 0), 1)
            self.draw_line(x_max, y_max, x_min, y_max, (255, 255, 0), 1)
            self.draw_line(x_min, y_max, x_min, y_min, (255, 255, 0), 1)

        # Draw forbidden zone (transparent red vertical band)
        bounds = sandbox.get_terrain_bounds()
        fz = bounds.get("forbidden_zone")
        if fz:
            fz_lo, fz_hi = fz
            # Draw dashed or solid indicator for forbidden zone
            self.draw_line(fz_lo, y_min, fz_lo, y_max, (255, 100, 100), 1)
            self.draw_line(fz_hi, y_min, fz_hi, y_max, (255, 100, 100), 1)
            # Connecting indicator at top
            self.draw_line(fz_lo, y_max, fz_hi, y_max, (255, 100, 100), 1)
