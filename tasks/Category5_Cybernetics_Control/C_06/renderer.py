"""
C-06: The Governor task rendering module
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class C06Renderer(Renderer):
    """C-06: The Governor. Draws anchor and wheel."""

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        self.set_camera_offset(camera_offset_x, 0)
        self.clear((30, 30, 30))

        anchor = (
            sandbox._terrain_bodies.get("anchor")
            if hasattr(sandbox, "_terrain_bodies")
            else None
        )
        wheel = (
            sandbox._terrain_bodies.get("wheel")
            if hasattr(sandbox, "_terrain_bodies")
            else None
        )

        for body in sandbox.world.bodies:
            if body.type == staticBody:
                self.draw_body(
                    body,
                    dynamic_color=(100, 150, 240),
                    static_color=(100, 100, 100),
                    outline_color=(180, 180, 180),
                    outline_width=2,
                )
            elif body.type == dynamicBody:
                if body == wheel:
                    self.draw_body(
                        body,
                        dynamic_color=(255, 180, 80),
                        static_color=(150, 100, 50),
                        outline_color=(255, 220, 140),
                        outline_width=3,
                    )
                else:
                    self.draw_body(
                        body,
                        dynamic_color=(100, 200, 100),  # Green dynamic objects
                        static_color=(150, 100, 50),
                        outline_color=(50, 150, 50),
                        outline_width=2,
                    )
