"""
C-01: The Cart-Pole task rendering module
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class C01Renderer(Renderer):
    """C-01: The Cart-Pole task renderer. Draws track, cart, and pole."""

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        self.set_camera_offset(camera_offset_x, 0)
        self.clear((30, 30, 30))

        # Track (static)
        for body in sandbox.world.bodies:
            if body.type == staticBody:
                self.draw_body(
                    body,
                    dynamic_color=(100, 150, 240),
                    static_color=(120, 120, 120),
                    outline_color=(180, 180, 180),
                    outline_width=2,
                )

        # Cart and pole (dynamic)
        cart = sandbox._terrain_bodies.get("cart") if hasattr(sandbox, "_terrain_bodies") else None
        pole = sandbox._terrain_bodies.get("pole") if hasattr(sandbox, "_terrain_bodies") else None

        for body in sandbox.world.bodies:
            if body.type != dynamicBody:
                continue
            if body == cart:
                self.draw_body(
                    body,
                    dynamic_color=(255, 180, 80),
                    static_color=(150, 100, 50),
                    outline_color=(255, 220, 140),
                    outline_width=3,
                )
            elif body == pole:
                self.draw_body(
                    body,
                    dynamic_color=(100, 200, 255),
                    static_color=(80, 160, 200),
                    outline_color=(150, 220, 255),
                    outline_width=2,
                )
            else:
                self.draw_body(
                    body,
                    dynamic_color=(100, 200, 100),  # Green dynamic objects
                    static_color=(150, 100, 50),
                    outline_color=(50, 150, 50),
                    outline_width=2,
                )

