"""
F-06: The Pipeline task rendering module
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class F06Renderer(Renderer):
    """F-06: The Pipeline task specific renderer"""

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        self.set_camera_offset(camera_offset_x)
        self.clear((30, 30, 30))  # Dark background consistent with other categories

        for body in sandbox.world.bodies:
            if body.type == staticBody:
                is_source = sandbox._terrain_bodies.get("source") == body
                is_target = sandbox._terrain_bodies.get("target") == body
                if is_source:
                    self.draw_body(
                        body,
                        dynamic_color=(80, 140, 180),
                        static_color=(60, 120, 160),
                        outline_color=(100, 160, 200),
                        outline_width=2,
                    )
                elif is_target:
                    self.draw_body(
                        body,
                        dynamic_color=(80, 160, 120),
                        static_color=(60, 140, 100),
                        outline_color=(100, 180, 140),
                        outline_width=2,
                    )
                else:
                    self.draw_body(
                        body,
                        dynamic_color=(100, 150, 240),
                        static_color=(95, 90, 80),
                        outline_color=(140, 130, 110),
                        outline_width=2,
                    )

        if hasattr(sandbox, "_fluid_particles"):
            default_radius = getattr(sandbox, "_PARTICLE_RADIUS", 0.10)
            for p in sandbox._fluid_particles:
                if p is not None and p.active:
                    px, py = p.position.x, p.position.y
                    r = default_radius
                    for f in p.fixtures:
                        if hasattr(f.shape, "radius"):
                            r = f.shape.radius
                            break
                    self.draw_circle(px, py, r, (100, 160, 220), outline_color=(130, 190, 255), outline_width=1)

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
        # Pit 1 (loss)
        if hasattr(sandbox, "PIT_X_MIN"):
            px1, px2 = sandbox.PIT_X_MIN, sandbox.PIT_X_MAX
            py1, py2 = sandbox.PIT_Y_MIN, sandbox.PIT_Y_MAX
            self.draw_line(px1, py1, px2, py1, (180, 50, 50), 2)
            self.draw_line(px2, py1, px2, py2, (180, 50, 50), 2)
            self.draw_line(px2, py2, px1, py2, (180, 50, 50), 2)
            self.draw_line(px1, py2, px1, py1, (180, 50, 50), 2)
        # Pit 2 (loss)
        if hasattr(sandbox, "PIT2_X_MIN"):
            qx1, qx2 = sandbox.PIT2_X_MIN, sandbox.PIT2_X_MAX
            qy1, qy2 = sandbox.PIT2_Y_MIN, sandbox.PIT2_Y_MAX
            self.draw_line(qx1, qy1, qx2, qy1, (160, 40, 40), 2)
            self.draw_line(qx2, qy1, qx2, qy2, (160, 40, 40), 2)
            self.draw_line(qx2, qy2, qx1, qy2, (160, 40, 40), 2)
            self.draw_line(qx1, qy2, qx1, qy1, (160, 40, 40), 2)
        # Pit 3 (loss)
        if hasattr(sandbox, "PIT3_X_MIN"):
            rx1, rx2 = sandbox.PIT3_X_MIN, sandbox.PIT3_X_MAX
            ry1, ry2 = sandbox.PIT3_Y_MIN, sandbox.PIT3_Y_MAX
            self.draw_line(rx1, ry1, rx2, ry1, (200, 60, 60), 2)
            self.draw_line(rx2, ry1, rx2, ry2, (200, 60, 60), 2)
            self.draw_line(rx2, ry2, rx1, ry2, (200, 60, 60), 2)
            self.draw_line(rx1, ry2, rx1, ry1, (200, 60, 60), 2)
        # Headwind threshold (blue dotted line)
        if hasattr(sandbox, "HEADWIND_Y_THRESHOLD"):
            y_thresh = sandbox.HEADWIND_Y_THRESHOLD
            self.draw_line(0, y_thresh, 26, y_thresh, (100, 100, 255), 1)
        # Gravity well (purple rectangle)
        if hasattr(sandbox, "GRAVWELL_X_MIN"):
            gx1, gx2 = sandbox.GRAVWELL_X_MIN, sandbox.GRAVWELL_X_MAX
            gy1, gy2 = sandbox.GRAVWELL_Y_MIN, sandbox.GRAVWELL_Y_MAX
            self.draw_line(gx1, gy1, gx2, gy1, (180, 100, 255), 1)
            self.draw_line(gx2, gy1, gx2, gy2, (180, 100, 255), 1)
            self.draw_line(gx2, gy2, gx1, gy2, (180, 100, 255), 1)
            self.draw_line(gx1, gy2, gx1, gy1, (180, 100, 255), 1)