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

    def render(self, sandbox, agent_body, _target_x, camera_offset_x):
        # Dynamic Viewport: center on the track_center_x
        if hasattr(sandbox, "get_terrain_bounds") and callable(getattr(sandbox, "get_terrain_bounds")):
            bounds = sandbox.get_terrain_bounds()
        else:
            bounds = {}
        track_center_x = float(
            bounds.get("track_center_x", getattr(sandbox, "TRACK_CENTER_X", 10.0))
        )
        track_y = float(
            bounds.get(
                "cart_rail_center_y",
                getattr(sandbox, "cart_rail_center_y", getattr(sandbox, "CART_RAIL_CENTER_Y", 2.0)),
            )
        )
        w = float(self.simulator.screen_width)
        h = float(self.simulator.screen_height)
        ppm = 40.0
        # World x at horizontal screen center = track_center_x (plus caller pan in px)
        pan_x = float(camera_offset_x or 0.0)
        fixed_offset_x = track_center_x * ppm - w / 2.0 + pan_x
        # Keep prior framing: world (track_y + 1) m at vertical screen center
        fixed_offset_y = h / 2.0 - (track_y + 1.0) * ppm
        
        self.set_camera_offset(fixed_offset_x, fixed_offset_y)
        self.clear((0, 0, 0))  # Pure Black Background

        # Academic Palette
        ENVIRONMENT_COLOR = (230, 194, 41)  # #E6C229 (Goldenrod Yellow)
        AGENT_COLOR = (76, 175, 80)        # #4CAF50 (Material Green)
        OUTLINE_COLOR = (255, 255, 255)

        # Draw Track (Environmental Baseline; matches Sandbox rail height when bounds expose it)
        safe_half_range = float(
            bounds.get("safe_half_range", getattr(sandbox, "SAFE_HALF_RANGE", 8.5))
        )
        track_x_start = track_center_x - safe_half_range
        track_x_end = track_center_x + safe_half_range
        
        self.draw_line(track_x_start, track_y, track_x_end, track_y, ENVIRONMENT_COLOR, width=4)
        # Draw track limits
        self.draw_line(track_x_start, track_y - 0.2, track_x_start, track_y + 0.2, ENVIRONMENT_COLOR, width=4)
        self.draw_line(track_x_end, track_y - 0.2, track_x_end, track_y + 0.2, ENVIRONMENT_COLOR, width=4)

        # Cart and pole (Agent-Created Structure) — use public accessors
        cart = sandbox.get_cart_body() if callable(getattr(sandbox, "get_cart_body", None)) else None
        pole = sandbox.get_pole_body() if callable(getattr(sandbox, "get_pole_body", None)) else None

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
