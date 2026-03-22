"""
C-05: The Logic Lock task rendering module
"""
import sys
import os
import pygame

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class C05Renderer(Renderer):
    """C-05: The Logic Lock. Draws ground, agent, and zone outlines A, B, C."""

    def __init__(self, simulator):
        super().__init__(simulator)
        # Enforce 16:9 aspect ratio and panoramic viewport
        # Ground length is 12m. Screen width 800px => ppm = 800/12 = 66.67
        self.simulator.ppm = 800.0 / 12.0
        self.simulator.screen_height = int(self.simulator.screen_width * 9 / 16)
        if self.simulator.can_display:
            # Re-create surface to match new aspect ratio
            self.simulator.screen = pygame.Surface((self.simulator.screen_width, self.simulator.screen_height))

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        # Panoramic viewport: world x in [0, 12], y in [0, 6.75]. target_x reserved for follow-camera callers.
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

        barrier_body = getattr(sandbox, "_terrain_bodies", {}).get("barrier")
        for body in sandbox.world.bodies:
            if body.type == staticBody:
                is_barrier = body is barrier_body
                color = (200, 80, 80) if is_barrier else ENVIRONMENT_COLOR
                self.draw_body(
                    body,
                    dynamic_color=color,
                    static_color=color,
                    outline_color=OUTLINE_COLOR,
                    outline_width=2,
                )
            elif body == agent:
                # Agent-Created Structure
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

        # Draw zone outlines (Environmental target zones)
        if hasattr(sandbox, "_zones"):
            for name, (cx, cy, hw, hh) in sandbox._zones.items():
                x1, y1 = cx - hw, cy - hh
                x2, y2 = cx + hw, cy + hh
                self.draw_line(x1, y1, x2, y1, ENVIRONMENT_COLOR, 1)
                self.draw_line(x2, y1, x2, y2, ENVIRONMENT_COLOR, 1)
                self.draw_line(x2, y2, x1, y2, ENVIRONMENT_COLOR, 1)
                self.draw_line(x1, y2, x1, y1, ENVIRONMENT_COLOR, 1)
