"""
E-05: The Magnet task rendering module.
"""
import sys
import os
import pygame
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class E05Renderer(Renderer):
    """E-05: The Magnet task specific renderer."""

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

        # Arena width is roughly 45m.
        # To fit 45m width in 1280px: PPM = 1280 / 45 = 28.444...
        self.simulator.ppm = 1280.0 / 45.0
        
        # Visible world height at PPM 28.44 is ~25.3m.
        # Place y=0 at 2 meters from bottom: offset_y = 2 * PPM pixels.
        self.set_camera_offset(0, 2 * self.simulator.ppm)

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        # Fixed panoramic view
        self.clear((0, 0, 0))

        # Academic Palette
        COLOR_ENV = (230, 194, 41)    # #E6C229 Goldenrod Yellow
        COLOR_AGENT = (76, 175, 80)   # #4CAF50 Material Green
        COLOR_OUTLINE = (50, 50, 50)
        COLOR_TARGET = (200, 100, 50) # Muted red/orange for target

        # Draw static terrain (ground)
        for body in sandbox.world.bodies:
            if body.type == staticBody:
                self.draw_body(
                    body,
                    static_color=COLOR_ENV,
                    outline_color=COLOR_OUTLINE,
                    outline_width=1,
                )

        # Draw the body and any other dynamic bodies
        for body in sandbox.world.bodies:
            if body.type == dynamicBody:
                is_body = False
                if hasattr(sandbox, "_terrain_bodies"):
                    env_body = sandbox._terrain_bodies.get("body")
                    if body == env_body:
                        is_body = True
                
                # Check if body is in sandbox.bodies (agent-added if any)
                if hasattr(sandbox, "bodies") and body in sandbox.bodies:
                    is_agent_body = True
                else:
                    is_agent_body = False

                if is_body or is_agent_body:
                    self.draw_body(
                        body,
                        dynamic_color=COLOR_AGENT,
                        outline_color=COLOR_OUTLINE,
                        outline_width=1,
                    )
                else:
                    # Other environment dynamic bodies
                    self.draw_body(
                        body,
                        dynamic_color=COLOR_ENV,
                        outline_color=COLOR_OUTLINE,
                        outline_width=1,
                    )

        # Target zone
        bounds = sandbox.get_terrain_bounds()
        tz = bounds.get("target_zone", {})
        tx_min = tz.get("x_min", 28.0)
        tx_max = tz.get("x_max", 32.0)
        ty_min = tz.get("y_min", 6.0)
        ty_max = tz.get("y_max", 9.0)
        self.draw_line(tx_min, ty_min, tx_max, ty_min, COLOR_TARGET, 2)
        self.draw_line(tx_max, ty_min, tx_max, ty_max, COLOR_TARGET, 2)
        self.draw_line(tx_max, ty_max, tx_min, ty_max, COLOR_TARGET, 2)
        self.draw_line(tx_min, ty_max, tx_min, ty_min, COLOR_TARGET, 2)
