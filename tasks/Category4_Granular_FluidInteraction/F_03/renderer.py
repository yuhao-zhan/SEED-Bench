"""
F-03: The Excavator — rendering module.
Pit x=[0,5], Hopper at (-5, 3), base at (-2, 0).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class F03Renderer(Renderer):
    """F-03: The Excavator renderer (pit, hopper, excavator)."""

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        self.set_camera_offset(camera_offset_x)
        self.clear((30, 30, 30))  # Dark background consistent with other categories

        for body in sandbox.world.bodies:
            if body.type == staticBody:
                is_hopper = False
                for key in ("hopper",):
                    if sandbox._terrain_bodies.get(key) == body:
                        is_hopper = True
                        break
                if is_hopper:
                    self.draw_body(
                        body,
                        dynamic_color=(80, 80, 120),
                        static_color=(90, 70, 50),
                        outline_color=(140, 110, 80),
                        outline_width=2,
                    )
                elif sandbox._terrain_bodies.get("central_wall") == body:
                    self.draw_body(
                        body,
                        dynamic_color=(120, 60, 60),
                        static_color=(100, 50, 50),
                        outline_color=(160, 80, 80),
                        outline_width=2,
                    )
                else:
                    self.draw_body(
                        body,
                        dynamic_color=(100, 150, 240),
                        static_color=(110, 95, 70),
                        outline_color=(160, 140, 100),
                        outline_width=2,
                    )

        if hasattr(sandbox, "_particles"):
            for p in sandbox._particles:
                if p is not None and p.active:
                    px, py = p.position.x, p.position.y
                    r = 0.06
                    for f in p.fixtures:
                        if hasattr(f.shape, "radius"):
                            r = f.shape.radius
                            break
                    in_hopper = (
                        hasattr(sandbox, "HOPPER_X_MIN")
                        and sandbox.HOPPER_X_MIN <= px <= sandbox.HOPPER_X_MAX
                        and sandbox.HOPPER_Y_MIN <= py <= sandbox.HOPPER_Y_MAX
                    )
                    if in_hopper:
                        self.draw_circle(px, py, r, (100, 220, 100), outline_color=(140, 255, 140), outline_width=2)
                    else:
                        self.draw_circle(px, py, r, (180, 200, 100), outline_color=(200, 220, 120), outline_width=1)

        for body in sandbox._bodies:
            if body.active:
                self.draw_body(
                    body,
                    dynamic_color=(100, 200, 100),  # Green dynamic objects
                    static_color=(100, 200, 100),
                    outline_color=(50, 150, 50),
                    outline_width=2,
                )

        if hasattr(sandbox, "BUILD_ZONE_X_MIN"):
            x_min = sandbox.BUILD_ZONE_X_MIN
            x_max = sandbox.BUILD_ZONE_X_MAX
            y_min = sandbox.BUILD_ZONE_Y_MIN
            y_max = sandbox.BUILD_ZONE_Y_MAX
            self.draw_line(x_min, y_min, x_max, y_min, (255, 255, 0), 1)
            self.draw_line(x_max, y_min, x_max, y_max, (255, 255, 0), 1)
            self.draw_line(x_max, y_max, x_min, y_max, (255, 255, 0), 1)
            self.draw_line(x_min, y_max, x_min, y_min, (255, 255, 0), 1)
