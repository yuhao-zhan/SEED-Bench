"""
E-01: Inverted Gravity task rendering module.
"""
import sys
import os
import pygame
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class E01Renderer(Renderer):
    """E-01: Inverted Gravity task specific renderer."""

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

        # Arena bounds are [0, 40] in X and [0, 20] in Y.
        # To fit 40m width in 1280px: PPM = 1280 / 40 = 32.
        self.simulator.ppm = 32.0
        
        # Visible world height at PPM 32 is 720 / 32 = 22.5m.
        # Arena height is 20m. We center it vertically.
        # Vertical padding is (22.5 - 20) / 2 = 1.25m.
        # offset_y = padding * PPM = 1.25 * 32 = 40 pixels.
        self.set_camera_offset(0, 40)

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        # Fixed panoramic view on the [0, 40] arena
        self.clear((0, 0, 0))

        # Academic Palette
        COLOR_ENV = (230, 194, 41)    # #E6C229 Goldenrod Yellow
        COLOR_AGENT = (76, 175, 80)   # #4CAF50 Material Green
        COLOR_OUTLINE = (50, 50, 50)
        COLOR_GUIDE = (100, 100, 100)
        COLOR_ARENA = (60, 60, 60)

        # Draw static terrain (floor, ceiling, walls, obstacles)
        for body in sandbox.world.bodies:
            if body.type == staticBody:
                self.draw_body(
                    body,
                    static_color=COLOR_ENV,
                    outline_color=COLOR_OUTLINE,
                    outline_width=1,
                )

        # Draw dynamic bodies (demonstrators + agent structure)
        for body in sandbox.world.bodies:
            if body.type == dynamicBody:
                is_agent_body = True
                if hasattr(sandbox, "_terrain_bodies"):
                    for key, value in sandbox._terrain_bodies.items():
                        if key.startswith("demonstrator_") and body == value:
                            is_agent_body = False
                            break
                
                # Check if body is in sandbox.bodies (agent beams)
                if hasattr(sandbox, "bodies") and body in sandbox.bodies:
                    is_agent_body = True
                
                if is_agent_body:
                    self.draw_body(
                        body,
                        dynamic_color=COLOR_AGENT,
                        outline_color=COLOR_OUTLINE,
                        outline_width=1,
                    )
                else:
                    # Demonstrators or other environment dynamic bodies
                    self.draw_body(
                        body,
                        dynamic_color=COLOR_ENV,
                        outline_color=COLOR_OUTLINE,
                        outline_width=1,
                    )

        # Build zone outline
        if hasattr(sandbox, "BUILD_ZONE_X_MIN"):
            x_min = sandbox.BUILD_ZONE_X_MIN
            x_max = sandbox.BUILD_ZONE_X_MAX
            y_min = sandbox.BUILD_ZONE_Y_MIN
            y_max = sandbox.BUILD_ZONE_Y_MAX
            self.draw_line(x_min, y_min, x_max, y_min, COLOR_GUIDE, 1)
            self.draw_line(x_max, y_min, x_max, y_max, COLOR_GUIDE, 1)
            self.draw_line(x_max, y_max, x_min, y_max, COLOR_GUIDE, 1)
            self.draw_line(x_min, y_max, x_min, y_min, COLOR_GUIDE, 1)

        # Arena boundary
        ax_min = getattr(sandbox, "ARENA_X_MIN", 0)
        ax_max = getattr(sandbox, "ARENA_X_MAX", 40)
        ay_min = getattr(sandbox, "ARENA_Y_MIN", 0)
        ay_max = getattr(sandbox, "ARENA_Y_MAX", 20)
        self.draw_line(ax_min, ay_min, ax_max, ay_min, COLOR_ARENA, 1)
        self.draw_line(ax_max, ay_min, ax_max, ay_max, COLOR_ARENA, 1)
        self.draw_line(ax_max, ay_max, ax_min, ay_max, COLOR_ARENA, 1)
        self.draw_line(ax_min, ay_max, ax_min, ay_min, COLOR_ARENA, 1)
