"""
C-01: The Cart-Pole task rendering module
"""
import sys
import os
import pygame

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class C01Renderer(Renderer):
    """C-01: The Cart-Pole task renderer. Draws track, cart, and pole."""

    def __init__(self, simulator):
        super().__init__(simulator)
        # Enforce 16:9 aspect ratio
        self.simulator.screen_height = int(self.simulator.screen_width * 9 / 16)
        if self.simulator.can_display:
            # Re-create surface to match new aspect ratio
            self.simulator.screen = pygame.Surface((self.simulator.screen_width, self.simulator.screen_height))

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        # Panoramic Viewport: capture the complete, un-truncated range of the track
        # Track is from 1.5 to 18.5, center 10.0. Track length 17m.
        # Screen width 800px / 40ppm = 20m.
        # Center of screen (400px) should be 10.0m.
        # 400 = 10.0 * 40 - offset_x => offset_x = 0
        fixed_offset_x = 0
        
        # Screen height 450px / 40ppm = 11.25m.
        # Center of screen (225px) at y=3.0m (track is at y=2.0m).
        # 225 = 450 - (3.0 * 40) - offset_y => 225 = 450 - 120 - offset_y => offset_y = 105
        fixed_offset_y = 105
        
        self.set_camera_offset(fixed_offset_x, fixed_offset_y)
        self.clear((0, 0, 0))  # Pure Black Background

        # Academic Palette
        ENVIRONMENT_COLOR = (230, 194, 41)  # #E6C229 (Goldenrod Yellow)
        AGENT_COLOR = (76, 175, 80)        # #4CAF50 (Material Green)
        OUTLINE_COLOR = (255, 255, 255)

        # Draw Track (Environmental Baseline)
        track_y = 2.0
        track_center_x = 10.0
        safe_half_range = 8.5
        track_x_start = track_center_x - safe_half_range
        track_x_end = track_center_x + safe_half_range
        
        self.draw_line(track_x_start, track_y, track_x_end, track_y, ENVIRONMENT_COLOR, width=4)
        # Draw track limits
        self.draw_line(track_x_start, track_y - 0.2, track_x_start, track_y + 0.2, ENVIRONMENT_COLOR, width=4)
        self.draw_line(track_x_end, track_y - 0.2, track_x_end, track_y + 0.2, ENVIRONMENT_COLOR, width=4)

        # Cart and pole (Agent-Created Structure)
        cart = sandbox._terrain_bodies.get("cart") if hasattr(sandbox, "_terrain_bodies") else None
        pole = sandbox._terrain_bodies.get("pole") if hasattr(sandbox, "_terrain_bodies") else None

        for body in sandbox.world.bodies:
            if body == cart or body == pole:
                self.draw_body(
                    body,
                    dynamic_color=AGENT_COLOR,
                    static_color=AGENT_COLOR,
                    outline_color=OUTLINE_COLOR,
                    outline_width=2,
                )
            elif body.type == staticBody:
                self.draw_body(
                    body,
                    dynamic_color=ENVIRONMENT_COLOR,
                    static_color=ENVIRONMENT_COLOR,
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
