"""
C-04: The Escaper task rendering module
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class C04Renderer(Renderer):
    """C-04: The Escaper. Draws maze walls and agent."""

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        self.set_camera_offset(camera_offset_x, 0)
        self.clear((30, 30, 30))

        # Draw all static bodies (maze walls)
        for body in sandbox.world.bodies:
            if body.type == staticBody:
                self.draw_body(
                    body,
                    dynamic_color=(100, 150, 240),
                    static_color=(80, 80, 100),
                    outline_color=(120, 120, 140),
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

        # Draw exit zone outline if available
        if hasattr(sandbox, "_exit_x_min"):
            ex = sandbox._exit_x_min
            ey_min = sandbox._exit_y_min
            ey_max = sandbox._exit_y_max
            self.draw_line(ex, ey_min, ex + 1.0, ey_min, (80, 255, 80), 2)
            self.draw_line(ex + 1.0, ey_min, ex + 1.0, ey_max, (80, 255, 80), 2)
            self.draw_line(ex + 1.0, ey_max, ex, ey_max, (80, 255, 80), 2)
            self.draw_line(ex, ey_max, ex, ey_min, (80, 255, 80), 2)
