"""
C-03: The Seeker task rendering module
"""
import sys
import os
import pygame
import math
import Box2D

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class C03Renderer(Renderer):
    """C-03: The Seeker. Draws ground, seeker, and target (virtual point)."""

    def __init__(self, simulator):
        super().__init__(simulator)
        # Enforce 16:9 aspect ratio and panoramic viewport
        # Ground length is 30m. Screen width 800px => ppm = 800/30 = 26.67
        self.simulator.ppm = 800.0 / 30.0
        self.simulator.screen_height = int(self.simulator.screen_width * 9 / 16)
        if self.simulator.can_display:
            # Re-create surface to match new aspect ratio
            self.simulator.screen = pygame.Surface((self.simulator.screen_width, self.simulator.screen_height))

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        # Panoramic Viewport: x in [0, 30], y in [0, 16.875]
        # offset_x = 0
        # offset_y = 20 (to show a bit below y=0)
        self.set_camera_offset(0, 20)
        self.clear((0, 0, 0))  # Pure Black Background

        # Academic Palette
        ENVIRONMENT_COLOR = (230, 194, 41)  # #E6C229 (Goldenrod Yellow)
        AGENT_COLOR = (76, 175, 80)        # #4CAF50 (Material Green)
        OUTLINE_COLOR = (255, 255, 255)

        seeker = (
            sandbox._terrain_bodies.get("seeker")
            if hasattr(sandbox, "_terrain_bodies")
            else None
        )

        for body in sandbox.world.bodies:
            if body.type == staticBody:
                # Environmental Baseline (Ground, Obstacles, Ice Zones)
                self.draw_body(
                    body,
                    dynamic_color=ENVIRONMENT_COLOR,
                    static_color=ENVIRONMENT_COLOR,
                    outline_color=OUTLINE_COLOR,
                    outline_width=2,
                )
            elif body == seeker:
                # Agent-Created Structure
                self.draw_body(
                    body,
                    dynamic_color=AGENT_COLOR,
                    static_color=AGENT_COLOR,
                    outline_color=OUTLINE_COLOR,
                    outline_width=2,
                )
            elif body.type == dynamicBody or (hasattr(Box2D.b2, "kinematicBody") and body.type == Box2D.b2.kinematicBody) or (not hasattr(Box2D.b2, "kinematicBody") and body.type == 1):
                # Kinematic or other dynamic bodies (Obstacles)
                self.draw_body(
                    body,
                    dynamic_color=ENVIRONMENT_COLOR,
                    static_color=ENVIRONMENT_COLOR,
                    outline_color=OUTLINE_COLOR,
                    outline_width=2,
                )

        # Draw target (Environmental target zone point)
        if hasattr(sandbox, "get_target_position_true"):
            tx, ty = sandbox.get_target_position_true()
            self.draw_circle(
                tx, ty, 0.25, ENVIRONMENT_COLOR, outline_color=OUTLINE_COLOR, outline_width=2
            )
        elif hasattr(sandbox, "get_target_position"):
            tx, ty = sandbox.get_target_position()
            self.draw_circle(
                tx, ty, 0.25, ENVIRONMENT_COLOR, outline_color=OUTLINE_COLOR, outline_width=2
            )
