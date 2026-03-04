"""
E-05: The Magnet task rendering module.
Magnets are invisible (not drawn); body and target zone are drawn.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class E05Renderer(Renderer):
    """E-05: The Magnet task specific renderer."""

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        self.set_camera_offset(camera_offset_x)
        self.clear((30, 30, 30))

        for body in sandbox.world.bodies:
            if body.type == staticBody:
                self.draw_body(
                    body,
                    dynamic_color=(100, 150, 240),
                    static_color=(70, 85, 90),
                    outline_color=(100, 120, 130),
                    outline_width=2,
                )

        for body in sandbox.world.bodies:
            if body.type == dynamicBody:
                is_body = False
                if hasattr(sandbox, "_terrain_bodies"):
                    env_body = sandbox._terrain_bodies.get("body")
                    if body == env_body:
                        is_body = True
                if is_body:
                    self.draw_body(
                        body,
                        dynamic_color=(120, 200, 255),
                        static_color=(70, 85, 90),
                        outline_color=(150, 220, 255),
                        outline_width=3,
                    )
                else:
                    self.draw_body(
                        body,
                        dynamic_color=(100, 200, 100),
                        static_color=(70, 85, 90),
                        outline_color=(50, 150, 50),
                        outline_width=2,
                    )

        # Target zone (red rectangle)
        bounds = sandbox.get_terrain_bounds()
        tz = bounds.get("target_zone", {})
        tx_min = tz.get("x_min", 28.0)
        tx_max = tz.get("x_max", 32.0)
        ty_min = tz.get("y_min", 6.0)
        ty_max = tz.get("y_max", 9.0)
        self.draw_line(tx_min, ty_min, tx_max, ty_min, (255, 0, 0), 2)
        self.draw_line(tx_max, ty_min, tx_max, ty_max, (255, 0, 0), 2)
        self.draw_line(tx_max, ty_max, tx_min, ty_max, (255, 0, 0), 2)
        self.draw_line(tx_min, ty_max, tx_min, ty_min, (255, 0, 0), 2)
