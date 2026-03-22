"""
C-04: The Escaper task rendering module
"""
import sys
import os
import pygame

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class C04Renderer(Renderer):
    """C-04: The Escaper. Draws maze walls and agent."""

    def __init__(self, simulator):
        super().__init__(simulator)
        # Enforce 16:9 aspect ratio and panoramic viewport
        # Maze x max is 20m. Screen width 800px => ppm = 40
        self.simulator.ppm = 40.0
        self.simulator.screen_height = int(self.simulator.screen_width * 9 / 16)
        if self.simulator.can_display:
            # Re-create surface to match new aspect ratio
            self.simulator.screen = pygame.Surface((self.simulator.screen_width, self.simulator.screen_height))

    def render(self, sandbox, agent_body, target_x=0.0, camera_offset_x=0.0):
        # World span x in [0, 20] m, y in [0, 3] m. camera_offset_x: screen-space pan (px); target_x reserved for follow-camera hooks.
        _ = target_x  # API parity with other task renderers
        self.set_camera_offset(float(camera_offset_x), 20)
        self.clear((0, 0, 0))  # Pure Black Background

        # Academic Palette
        ENVIRONMENT_COLOR = (230, 194, 41)  # #E6C229 (Goldenrod Yellow)
        AGENT_COLOR = (76, 175, 80)        # #4CAF50 (Material Green)
        OUTLINE_COLOR = (255, 255, 255)

        agent = (
            sandbox._terrain_bodies.get("agent")
            if hasattr(sandbox, "_terrain_bodies")
            else None
        )

        for body in sandbox.world.bodies:
            if body.type == staticBody:
                # Environmental Baseline (Maze walls)
                self.draw_body(
                    body,
                    dynamic_color=ENVIRONMENT_COLOR,
                    static_color=ENVIRONMENT_COLOR,
                    outline_color=OUTLINE_COLOR,
                    outline_width=2,
                )
            elif body == agent:
                # Controllable disk agent (task robot)
                self.draw_body(
                    body,
                    dynamic_color=AGENT_COLOR,
                    static_color=AGENT_COLOR,
                    outline_color=OUTLINE_COLOR,
                    outline_width=2,
                )
            elif body.type == dynamicBody:
                # Any other dynamic objects are also considered agent-related
                self.draw_body(
                    body,
                    dynamic_color=AGENT_COLOR,
                    static_color=AGENT_COLOR,
                    outline_color=OUTLINE_COLOR,
                    outline_width=2,
                )

        # Draw exit zone outline (from get_terrain_bounds; sandbox does not set _exit_* attributes)
        if hasattr(sandbox, "get_terrain_bounds"):
            bounds = sandbox.get_terrain_bounds()
            ex = bounds.get("exit_x_min")
            ey_min = bounds.get("exit_y_min")
            ey_max = bounds.get("exit_y_max")
            if ex is not None and ey_min is not None and ey_max is not None:
                x1 = bounds.get("x_max", 20.0)
                self.draw_line(ex, ey_min, x1, ey_min, ENVIRONMENT_COLOR, 2)
                self.draw_line(x1, ey_min, x1, ey_max, ENVIRONMENT_COLOR, 2)
                self.draw_line(x1, ey_max, ex, ey_max, ENVIRONMENT_COLOR, 2)
                self.draw_line(ex, ey_max, ex, ey_min, ENVIRONMENT_COLOR, 2)
