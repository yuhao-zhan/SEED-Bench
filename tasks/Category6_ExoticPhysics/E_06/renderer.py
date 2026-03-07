"""
E-06: The Cantilever task rendering module.
"""
import sys
import os
import pygame
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class E06Renderer(Renderer):
    """E-06: The Cantilever task specific renderer."""

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
        COLOR_ZONE = (150, 50, 50)    # Muted red for forbidden zone
        COLOR_ANCHOR = (50, 150, 50)  # Muted green for allowed anchor zone

        # Draw static terrain (ground)
        for body in sandbox.world.bodies:
            if body.type == staticBody:
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

        bounds = sandbox.get_terrain_bounds()
        bz = bounds.get("build_zone", {})
        y_min = bz.get("y", [1.5, 8.0])[0]
        y_max = bz.get("y", [1.5, 8.0])[1]

        # Draw build zone outline
        if bz:
            x_min, x_max = bz["x"][0], bz["x"][1]
            self.draw_line(x_min, y_min, x_max, y_min, COLOR_GUIDE, 1)
            self.draw_line(x_max, y_min, x_max, y_max, COLOR_GUIDE, 1)
            self.draw_line(x_max, y_max, x_min, y_max, COLOR_GUIDE, 1)
            self.draw_line(x_min, y_max, x_min, y_min, COLOR_GUIDE, 1)

        # Draw forbidden zone
        fz = bounds.get("forbidden_zone")
        if fz:
            fz_lo, fz_hi = fz
            self.draw_line(fz_lo, y_min, fz_lo, y_max, COLOR_ZONE, 1)
            self.draw_line(fz_hi, y_min, fz_hi, y_max, COLOR_ZONE, 1)
            self.draw_line(fz_lo, y_max, fz_hi, y_max, COLOR_ZONE, 1)

        # Draw allowed anchor zone (on the ground)
        az = bounds.get("allowed_anchor_zone")
        if az:
            az_lo, az_hi = az
            ground_y = bounds.get("ground_y", 1.0)
            self.draw_line(az_lo, ground_y, az_hi, ground_y, COLOR_ANCHOR, 3)
