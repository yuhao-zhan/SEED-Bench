"""
F-01: The Dam task rendering module
Renders terrain, water particles, dam structure, and build zone.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class F01Renderer(Renderer):
    """F-01: The Dam task specific renderer"""

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        self.set_camera_offset(camera_offset_x)
        self.clear((30, 30, 30))  # Dark background consistent with other categories

        # Draw static terrain (floor, left wall)
        for body in sandbox.world.bodies:
            if body.type == staticBody:
                self.draw_body(
                    body,
                    dynamic_color=(100, 150, 240),
                    static_color=(120, 100, 80),
                    outline_color=(180, 160, 120),
                    outline_width=2,
                )

        # Draw water particles (blue circles)
        if hasattr(sandbox, "_water_particles"):
            for particle in sandbox._water_particles:
                if particle is not None and particle.active:
                    px, py = particle.position.x, particle.position.y
                    radius = 0.12
                    for f in particle.fixtures:
                        if hasattr(f.shape, "radius"):
                            radius = f.shape.radius
                            break
                    self.draw_circle(px, py, radius, (80, 140, 220), outline_color=(120, 180, 255), outline_width=1)

        # Draw dam structure (agent-built beams)
        for body in sandbox._bodies:
            if body.active:
                self.draw_body(
                    body,
                    dynamic_color=(80, 180, 120),
                    static_color=(80, 180, 120),
                    outline_color=(40, 120, 80),
                    outline_width=2,
                )

        # Draw downstream boundary line (red) at x = DOWNSTREAM_X_START
        if hasattr(sandbox, "DOWNSTREAM_X_START"):
            dx = sandbox.DOWNSTREAM_X_START
            self.draw_line(dx, 0, dx, 12, (255, 80, 80), 3)

        # Draw build zone outline (yellow)
        if hasattr(sandbox, "BUILD_ZONE_X_MIN"):
            x_min = sandbox.BUILD_ZONE_X_MIN
            x_max = sandbox.BUILD_ZONE_X_MAX
            y_min = sandbox.BUILD_ZONE_Y_MIN
            y_max = sandbox.BUILD_ZONE_Y_MAX
            self.draw_line(x_min, y_min, x_max, y_min, (255, 255, 0), 1)
            self.draw_line(x_max, y_min, x_max, y_max, (255, 255, 0), 1)
            self.draw_line(x_max, y_max, x_min, y_max, (255, 255, 0), 1)
            self.draw_line(x_min, y_max, x_min, y_min, (255, 255, 0), 1)
