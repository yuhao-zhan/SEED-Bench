"""
E-04: Variable Mass task rendering module.
"""
import sys
import os
import pygame
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class E04Renderer(Renderer):
    """E-04: Variable Mass task specific renderer."""

    def __init__(self, simulator):
        super().__init__(simulator)
        # Enforce 16:9 aspect ratio and panoramic viewport
        self.simulator.screen_width = 1280
        self.simulator.screen_height = 720
        
        # Re-initialize surface for 16:9 if it was already created
        if self.simulator.can_display:
            try:
                if not os.environ.get('DISPLAY'):
                    os.environ['SDL_VIDEODRIVER'] = 'dummy'
                self.simulator.screen = pygame.Surface((1280, 720))
            except Exception:
                pass

        # Arena width is 40m.
        # To fit 40m width in 1280px: PPM = 1280 / 40 = 32.
        self.simulator.ppm = 32.0
        
        # Visible world height at PPM 32 is 720 / 32 = 22.5m.
        # Place y=0 at 2 meters from bottom: offset_y = 2 * 32 = 64 pixels.
        self.set_camera_offset(0, 64)

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        # Fixed panoramic view
        self.clear((0, 0, 0))

        # Academic Palette
        COLOR_ENV = (230, 194, 41)    # #E6C229 Goldenrod Yellow
        COLOR_AGENT = (76, 175, 80)   # #4CAF50 Material Green
        COLOR_OUTLINE = (50, 50, 50)
        COLOR_GUIDE = (100, 100, 100)

        # Draw static or kinematic terrain (ground)
        for body in sandbox.world.bodies:
            # In E-04, ground is a kinematicBody to drive excitation
            if body.type != dynamicBody:
                self.draw_body(
                    body,
                    static_color=COLOR_ENV,
                    outline_color=COLOR_OUTLINE,
                    outline_width=1,
                )

        # Draw structure (dynamic bodies)
        for body in sandbox.world.bodies:
            if body.type == dynamicBody:
                # Check if body is in sandbox.bodies (agent beams)
                if hasattr(sandbox, "bodies") and body in sandbox.bodies:
                    self.draw_body(
                        body,
                        dynamic_color=COLOR_AGENT,
                        outline_color=COLOR_OUTLINE,
                        outline_width=1,
                    )
                else:
                    self.draw_body(
                        body,
                        dynamic_color=COLOR_ENV,
                        outline_color=COLOR_OUTLINE,
                        outline_width=1,
                    )

        # Build zone outline (use instance bounds from get_build_zone for consistency with evaluator)
        if hasattr(sandbox, "get_build_zone"):
            x_min, x_max, y_min, y_max = sandbox.get_build_zone()
            self.draw_line(x_min, y_min, x_max, y_min, COLOR_GUIDE, 1)
            self.draw_line(x_max, y_min, x_max, y_max, COLOR_GUIDE, 1)
            self.draw_line(x_max, y_max, x_min, y_max, COLOR_GUIDE, 1)
            self.draw_line(x_min, y_max, x_min, y_min, COLOR_GUIDE, 1)
