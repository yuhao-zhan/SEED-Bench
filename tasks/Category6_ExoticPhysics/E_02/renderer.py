"""
E-02: Thick Air task rendering module.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class E02Renderer(Renderer):
    """E-02: Thick Air task specific renderer."""

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        self.set_camera_offset(camera_offset_x)
        self.clear((30, 30, 30))

        # Draw static terrain (ground)
        for body in sandbox.world.bodies:
            if body.type == staticBody:
                self.draw_body(
                    body,
                    dynamic_color=(100, 150, 240),
                    static_color=(80, 90, 70),
                    outline_color=(120, 130, 100),
                    outline_width=2,
                )

        # Draw craft and any other dynamic bodies
        for body in sandbox.world.bodies:
            if body.type == dynamicBody:
                is_craft = False
                if hasattr(sandbox, "_terrain_bodies"):
                    craft = sandbox._terrain_bodies.get("craft")
                    if body == craft:
                        is_craft = True
                if is_craft:
                    self.draw_body(
                        body,
                        dynamic_color=(255, 180, 80),
                        static_color=(80, 90, 70),
                        outline_color=(255, 200, 120),
                        outline_width=3,
                    )
                else:
                    self.draw_body(
                        body,
                        dynamic_color=(100, 200, 100),
                        static_color=(80, 90, 70),
                        outline_color=(50, 150, 50),
                        outline_width=2,
                    )

        # Target zone (red rectangle)
        tx_min = getattr(sandbox, "TARGET_X_MIN", 28.0)
        tx_max = getattr(sandbox, "TARGET_X_MAX", 32.0)
        ty_min = getattr(sandbox, "TARGET_Y_MIN", 2.0)
        ty_max = getattr(sandbox, "TARGET_Y_MAX", 5.0)
        self.draw_line(tx_min, ty_min, tx_max, ty_min, (255, 0, 0), 2)
        self.draw_line(tx_max, ty_min, tx_max, ty_max, (255, 0, 0), 2)
        self.draw_line(tx_max, ty_max, tx_min, ty_max, (255, 0, 0), 2)
        self.draw_line(tx_min, ty_max, tx_min, ty_min, (255, 0, 0), 2)
