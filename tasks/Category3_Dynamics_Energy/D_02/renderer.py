"""
D-02: The Jumper task rendering module
Renders left platform, pit, right platform, build zone, jumper, and launcher.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class D02Renderer(Renderer):
    """D-02: The Jumper task renderer."""

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        self.set_camera_offset(camera_offset_x, 0)
        self.clear((30, 30, 30))

        # Draw static terrain (left and right platforms, and all red bars: lower + ceiling for each slot)
        barrier_bodies = []
        if hasattr(sandbox, "_terrain_bodies"):
            for key in ("barrier", "barrier2", "barrier3", "ceiling1", "ceiling2", "ceiling3"):
                b = sandbox._terrain_bodies.get(key)
                if b is not None:
                    barrier_bodies.append(b)
        for body in sandbox.world.bodies:
            if body.type == staticBody:
                if body in barrier_bodies:
                    self.draw_body(
                        body,
                        dynamic_color=(180, 80, 80),
                        static_color=(120, 60, 60),
                        outline_color=(220, 100, 100),
                        outline_width=2,
                    )
                else:
                    self.draw_body(
                        body,
                        dynamic_color=(100, 150, 240),
                        static_color=(150, 100, 50),
                        outline_color=(200, 150, 100),
                        outline_width=2,
                    )

        # Pit: visual band (dark) between platforms
        if hasattr(sandbox, "_left_platform_end_x") and hasattr(sandbox, "_right_platform_start_x"):
            x1 = sandbox._left_platform_end_x
            x2 = sandbox._right_platform_start_x
            self.draw_line(x1, 0, x2, 0, (60, 40, 40), 2)
            self.draw_line(x1, 1.0, x1, -1.0, (80, 50, 50), 1)
            self.draw_line(x2, 1.0, x2, -1.0, (80, 50, 50), 1)

        # Dynamic bodies: jumper vs launcher beams
        jumper_body = (
            sandbox._terrain_bodies.get("jumper")
            if hasattr(sandbox, "_terrain_bodies") else None
        )
        for body in sandbox.world.bodies:
            if body.type != dynamicBody:
                continue
            if body == jumper_body:
                self.draw_body(
                    body,
                    dynamic_color=(255, 180, 80),
                    static_color=(150, 100, 50),
                    outline_color=(255, 220, 140),
                    outline_width=3,
                )
            elif body in sandbox._bodies:
                self.draw_body(
                    body,
                    dynamic_color=(100, 200, 100),
                    static_color=(150, 100, 50),
                    outline_color=(50, 150, 50),
                    outline_width=2,
                )
            else:
                self.draw_body(
                    body,
                    dynamic_color=(100, 150, 240),
                    static_color=(150, 100, 50),
                    outline_color=(100, 150, 255),
                    outline_width=2,
                )

        # Build zone outline (yellow)
        if hasattr(sandbox, "BUILD_ZONE_X_MIN"):
            x_min = sandbox.BUILD_ZONE_X_MIN
            x_max = sandbox.BUILD_ZONE_X_MAX
            y_min = sandbox.BUILD_ZONE_Y_MIN
            y_max = sandbox.BUILD_ZONE_Y_MAX
            self.draw_line(x_min, y_min, x_max, y_min, (255, 255, 0), 1)
            self.draw_line(x_max, y_min, x_max, y_max, (255, 255, 0), 1)
            self.draw_line(x_max, y_max, x_min, y_max, (255, 255, 0), 1)
            self.draw_line(x_min, y_max, x_min, y_min, (255, 255, 0), 1)
