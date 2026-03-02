"""
C-05: The Logic Lock task rendering module
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class C05Renderer(Renderer):
    """C-05: The Logic Lock. Draws ground, agent, and zone outlines A, B, C."""

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        self.set_camera_offset(camera_offset_x, 0)
        self.clear((30, 30, 30))

        for body in sandbox.world.bodies:
            if body.type == staticBody:
                self.draw_body(
                    body,
                    dynamic_color=(100, 150, 240),
                    static_color=(80, 80, 60),
                    outline_color=(120, 120, 100),
                    outline_width=2,
                )

        agent = (
            sandbox._terrain_bodies.get("agent")
            if hasattr(sandbox, "_terrain_bodies")
            else None
        )
        for body in sandbox.world.bodies:
            if body.type != dynamicBody:
                continue
            if body == agent:
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

        # Draw zone outlines (A, B, C)
        if hasattr(sandbox, "_zones"):
            colors = {"A": (255, 150, 150), "B": (150, 255, 150), "C": (150, 150, 255)}
            for name, (cx, cy, hw, hh) in sandbox._zones.items():
                color = colors.get(name, (200, 200, 200))
                x1, y1 = cx - hw, cy - hh
                x2, y2 = cx + hw, cy + hh
                self.draw_line(x1, y1, x2, y1, color, 1)
                self.draw_line(x2, y1, x2, y2, color, 1)
                self.draw_line(x2, y2, x1, y2, color, 1)
                self.draw_line(x1, y2, x1, y1, color, 1)
