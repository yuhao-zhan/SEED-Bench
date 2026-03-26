"""
E-03: Slippery World task rendering module.
"""
import sys
import os
import pygame
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class E03Renderer(Renderer):
    """E-03: Slippery World task specific renderer."""

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

        # Arena width is roughly 50m.
        # To fit 50m width in 1280px: PPM = 1280 / 50 = 25.6.
        self.simulator.ppm = 25.6
        
        # Visible world height at PPM 25.6 is 720 / 25.6 = 28.125m.
        # Place y=0 at 2 meters from bottom: offset_y = 2 * 25.6 = 51.2 pixels.
        self.set_camera_offset(0, 51)

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        # Fixed panoramic view
        self.clear((0, 0, 0))

        # Academic Palette
        COLOR_ENV = (230, 194, 41)    # #E6C229 Goldenrod Yellow
        COLOR_AGENT = (76, 175, 80)   # #4CAF50 Material Green
        COLOR_OUTLINE = (50, 50, 50)
        COLOR_TARGET = (200, 100, 50) # Muted red/orange for target
        COLOR_CHECKPOINT = (100, 100, 200) # Muted blue for checkpoints
        COLOR_ZONE = (150, 150, 150) # Grey for general zones

        # Draw static terrain (ground)
        for body in sandbox.world.bodies:
            if body.type == staticBody:
                self.draw_body(
                    body,
                    static_color=COLOR_ENV,
                    outline_color=COLOR_OUTLINE,
                    outline_width=1,
                )

        # Draw Zones
        bounds = sandbox.get_terrain_bounds()
        zones_to_render = {
            "speed_penalty_zone": (255, 100, 100, 50),
            "reverse_thrust_zone": (255, 150, 50, 50),
            "vert_reverse_zone": (255, 50, 150, 50),
            "momentum_drain_zone": (100, 100, 100, 50),
            "wind_zone": (100, 200, 255, 50),
            "thrust_scale_zone": (200, 100, 255, 50),
            "oscillating_fx_zone": (100, 255, 100, 50),
        }
        for zone_key, color in zones_to_render.items():
            zone = bounds.get(zone_key)
            if zone:
                zx_min, zx_max = zone["x_min"], zone["x_max"]
                # Draw zone as a vertical band from y=0 to y=10
                self.draw_line(zx_min, 0, zx_max, 0, color[:3], 1)
                self.draw_line(zx_max, 0, zx_max, 10, color[:3], 1)
                self.draw_line(zx_max, 10, zx_min, 10, color[:3], 1)
                self.draw_line(zx_min, 10, zx_min, 0, color[:3], 1)

        # Draw sled and any other dynamic bodies
        for body in sandbox.world.bodies:
            if body.type == dynamicBody:
                is_sled = False
                if hasattr(sandbox, "_terrain_bodies"):
                    sled = sandbox._terrain_bodies.get("sled")
                    if body == sled:
                        is_sled = True
                
                # Check if body is in sandbox.bodies (agent beams)
                if hasattr(sandbox, "bodies") and body in sandbox.bodies:
                    is_agent_body = True
                else:
                    is_agent_body = False

                if is_sled or is_agent_body:
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

        # Draw Checkpoint zones
        bounds = sandbox.get_terrain_bounds()
        for zone_key in ("checkpoint_zone", "checkpoint_b_zone"):
            cz = bounds.get(zone_key)
            if cz:
                cx_min, cx_max = cz["x_min"], cz["x_max"]
                cy_min, cy_max = cz["y_min"], cz["y_max"]
                self.draw_line(cx_min, cy_min, cx_max, cy_min, COLOR_CHECKPOINT, 1)
                self.draw_line(cx_max, cy_min, cx_max, cy_max, COLOR_CHECKPOINT, 1)
                self.draw_line(cx_max, cy_max, cx_min, cy_max, COLOR_CHECKPOINT, 1)
                self.draw_line(cx_min, cy_max, cx_min, cy_min, COLOR_CHECKPOINT, 1)

        # Target zone
        tz = bounds.get("target_zone", {})
        tx_min = tz.get("x_min", 28.0)
        tx_max = tz.get("x_max", 32.0)
        ty_min = tz.get("y_min", 2.2)
        ty_max = tz.get("y_max", 2.8)
        self.draw_line(tx_min, ty_min, tx_max, ty_min, COLOR_TARGET, 2)
        self.draw_line(tx_max, ty_min, tx_max, ty_max, COLOR_TARGET, 2)
        self.draw_line(tx_max, ty_max, tx_min, ty_max, COLOR_TARGET, 2)
        self.draw_line(tx_min, ty_max, tx_min, ty_min, COLOR_TARGET, 2)
