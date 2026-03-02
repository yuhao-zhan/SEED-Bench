"""
E-01: Inverted Gravity task rendering module.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class E01Renderer(Renderer):
    """E-01: Inverted Gravity task specific renderer."""

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        self.set_camera_offset(camera_offset_x)
        self.clear((30, 30, 30))

        # Draw static terrain (floor, ceiling, walls); obstacles in distinct color
        obstacle_bodies = set()
        if hasattr(sandbox, "_terrain_bodies"):
            for key in ("obstacle_1", "obstacle_2", "obstacle_3"):
                b = sandbox._terrain_bodies.get(key)
                if b is not None:
                    obstacle_bodies.add(b)
        for body in sandbox.world.bodies:
            if body.type == staticBody:
                if body in obstacle_bodies:
                    self.draw_body(
                        body,
                        dynamic_color=(220, 100, 60),
                        static_color=(180, 70, 50),
                        outline_color=(255, 120, 80),
                        outline_width=2,
                    )
                else:
                    self.draw_body(
                        body,
                        dynamic_color=(100, 150, 240),
                        static_color=(80, 80, 90),
                        outline_color=(120, 120, 130),
                        outline_width=2,
                    )

        # Draw dynamic bodies (demonstrators + agent structure)
        for body in sandbox.world.bodies:
            if body.type == dynamicBody:
                is_demonstrator = False
                if hasattr(sandbox, "_terrain_bodies"):
                    for key, value in sandbox._terrain_bodies.items():
                        if key.startswith("demonstrator_") and body == value:
                            is_demonstrator = True
                            break
                if is_demonstrator:
                    self.draw_body(
                        body,
                        dynamic_color=(255, 180, 80),
                        static_color=(80, 80, 90),
                        outline_color=(255, 200, 120),
                        outline_width=2,
                    )
                else:
                    self.draw_body(
                        body,
                        dynamic_color=(100, 200, 100),
                        static_color=(80, 80, 90),
                        outline_color=(50, 150, 50),
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

        # Optional: arena boundary (thin red) for clarity
        ax_min = getattr(sandbox, "ARENA_X_MIN", 0)
        ax_max = getattr(sandbox, "ARENA_X_MAX", 40)
        ay_min = getattr(sandbox, "ARENA_Y_MIN", 0)
        ay_max = getattr(sandbox, "ARENA_Y_MAX", 20)
        self.draw_line(ax_min, ay_min, ax_max, ay_min, (200, 80, 80), 1)
        self.draw_line(ax_max, ay_min, ax_max, ay_max, (200, 80, 80), 1)
        self.draw_line(ax_max, ay_max, ax_min, ay_max, (200, 80, 80), 1)
        self.draw_line(ax_min, ay_max, ax_min, ay_min, (200, 80, 80), 1)
