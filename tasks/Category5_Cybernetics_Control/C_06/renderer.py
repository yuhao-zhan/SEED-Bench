"""
C-06: The Governor task rendering module
"""
import sys
import os
import pygame

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class C06Renderer(Renderer):
    """C-06: The Governor. Draws anchor and wheel."""

    def __init__(self, simulator):
        super().__init__(simulator)
        # Enforce 16:9 aspect ratio and panoramic viewport
        # Area of interest is centered at (5, 5) with a 10m width.
        # Screen width 800px => ppm = 80
        self.simulator.ppm = 80.0
        self.simulator.screen_height = int(self.simulator.screen_width * 9 / 16)
        if self.simulator.can_display:
            # Re-create surface to match new aspect ratio
            self.simulator.screen = pygame.Surface((self.simulator.screen_width, self.simulator.screen_height))

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        # Panoramic Viewport: x in [0, 10], y centered at 5.0
        # offset_x = 0 (for x=0 at screen_x=0)
        # offset_y = -175 (for y=5 at screen_y=225)
        self.set_camera_offset(0, -175)
        self.clear((0, 0, 0))  # Pure Black Background

        # Academic Palette — anchor = static env; wheel = motor-driven plant (not agent-built)
        ENVIRONMENT_COLOR = (230, 194, 41)  # #E6C229 (Goldenrod Yellow)
        WHEEL_COLOR = (255, 213, 79)  # Brighter amber for the task wheel
        AGENT_COLOR = (76, 175, 80)  # #4CAF50 — any extra agent-created bodies
        OUTLINE_COLOR = (255, 255, 255)

        wheel = sandbox.get_wheel_body() if hasattr(sandbox, "get_wheel_body") else None

        for body in sandbox.world.bodies:
            if body.type == staticBody:
                # Environmental Baseline (Anchor)
                self.draw_body(
                    body,
                    dynamic_color=ENVIRONMENT_COLOR,
                    static_color=ENVIRONMENT_COLOR,
                    outline_color=OUTLINE_COLOR,
                    outline_width=2,
                )
            elif body == wheel:
                self.draw_body(
                    body,
                    dynamic_color=WHEEL_COLOR,
                    static_color=WHEEL_COLOR,
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
