"""
D-04: The Swing task rendering module
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class D04Renderer(Renderer):
    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        self.set_camera_offset(camera_offset_x, 0)
        self.clear((30, 30, 30))
        for body in sandbox.world.bodies:
            if body.type == staticBody:
                self.draw_body(body, dynamic_color=(100, 150, 240), static_color=(150, 100, 50),
                    outline_color=(200, 150, 100), outline_width=2)
        seat = sandbox._terrain_bodies.get("swing_seat") if hasattr(sandbox, "_terrain_bodies") else None
        pivot = sandbox._terrain_bodies.get("pivot") if hasattr(sandbox, "_terrain_bodies") else None
        for body in sandbox.world.bodies:
            if body.type != dynamicBody:
                continue
            if body == seat:
                self.draw_body(body, dynamic_color=(255, 180, 80), static_color=(150, 100, 50),
                    outline_color=(255, 220, 140), outline_width=3)
            elif body in sandbox._bodies:
                self.draw_body(body, dynamic_color=(100, 200, 100), static_color=(150, 100, 50),
                    outline_color=(50, 150, 50), outline_width=2)
            else:
                self.draw_body(body, dynamic_color=(100, 150, 240), static_color=(150, 100, 50),
                    outline_color=(100, 150, 255), outline_width=2)
        if hasattr(sandbox, "_target_y_min"):
            y_min = sandbox._target_y_min
            x_min = sandbox._target_x_min
            x_max = sandbox._target_x_max
            self.draw_line(x_min, y_min, x_max, y_min, (255, 80, 80), 2)
            self.draw_line(x_min, y_min, x_min, y_min + 1.0, (255, 80, 80), 2)
            self.draw_line(x_max, y_min, x_max, y_min + 1.0, (255, 80, 80), 2)
        if hasattr(sandbox, "BUILD_ZONE_X_MIN"):
            x_min, x_max = sandbox.BUILD_ZONE_X_MIN, sandbox.BUILD_ZONE_X_MAX
            y_min, y_max = sandbox.BUILD_ZONE_Y_MIN, sandbox.BUILD_ZONE_Y_MAX
            self.draw_line(x_min, y_min, x_max, y_min, (255, 255, 0), 1)
            self.draw_line(x_max, y_min, x_max, y_max, (255, 255, 0), 1)
            self.draw_line(x_max, y_max, x_min, y_max, (255, 255, 0), 1)
            self.draw_line(x_min, y_max, x_min, y_min, (255, 255, 0), 1)
