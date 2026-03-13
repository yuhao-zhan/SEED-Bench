"""
F-02: The Amphibian task rendering module
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class F02Renderer(Renderer):
    """F-02: The Amphibian task specific renderer"""

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        # Enforce 16:9 aspect ratio and 1280x720 resolution
        if self.simulator.screen_width != 1280 or self.simulator.screen_height != 720:
            self.simulator.screen_width = 1280
            self.simulator.screen_height = 720
            if self.simulator.can_display:
                import pygame
                self.simulator.screen = pygame.Surface((1280, 720))

        # Panoramic viewport: fix PPM and offset to see the entire relevant area
        # 1280 / 35 = 36.5 PPM captures the full 35m width
        self.simulator.ppm = 35
        self.set_camera_offset(0, 0)
        
        self.clear((0, 0, 0))  # Background: Pure Black

        # Academic Colors
        COLOR_ENVIRONMENT = (230, 194, 41)   # #E6C229: Goldenrod Yellow
        COLOR_STRUCTURE = (76, 175, 80)      # #4CAF50: Material Green
        COLOR_WATER = (70, 130, 180)         # Professional Steel Blue
        COLOR_WATER_OUTLINE = (100, 160, 220)

        for body in sandbox.world.bodies:
            if body.type == staticBody:
                is_water = False
                for fixture in body.fixtures:
                    if getattr(fixture, 'isSensor', False):
                        is_water = True
                        break
                if is_water:
                    self.draw_body(
                        body,
                        dynamic_color=COLOR_WATER,
                        static_color=COLOR_WATER,
                        outline_color=COLOR_WATER_OUTLINE,
                        outline_width=2,
                    )
                else:
                    self.draw_body(
                        body,
                        dynamic_color=COLOR_ENVIRONMENT,
                        static_color=COLOR_ENVIRONMENT,
                        outline_color=(160, 140, 110),
                        outline_width=2,
                    )

        for body in sandbox._bodies:
            if body.active:
                self.draw_body(
                    body,
                    dynamic_color=COLOR_STRUCTURE,
                    static_color=COLOR_STRUCTURE,
                    outline_color=(50, 150, 50),
                    outline_width=2,
                )

        # --- NEW HIGH DIFFICULTY VISUALS ---
        # EMP Zone: Semi-transparent purple/magenta overlay
        if hasattr(sandbox, "_emp_zone") and sandbox._emp_zone is not None:
            ex1, ex2 = sandbox._emp_zone
            self.draw_rect(ex1, 0, ex2 - ex1, 8, (128, 0, 128, 60)) # Purple tint
            
        # Corrosive Ceiling: Red hazy line
        if hasattr(sandbox, "_corrosive_y") and sandbox._corrosive_y < 1000:
            cy = sandbox._corrosive_y
            self.draw_line(0, cy, 35, cy, (255, 0, 0, 150), 4) # Red boundary
            
        # Whirlpool: Swirling blue/cyan circles or just a region tint
        if hasattr(sandbox, "_whirlpool") and sandbox._whirlpool is not None:
            wx = float(sandbox._whirlpool.get("x", 17.0))
            ww = float(sandbox._whirlpool.get("width", 2.0))
            self.draw_rect(wx - ww/2.0, 0, ww, 2, (0, 255, 255, 60)) # Cyan tint in water

        if hasattr(sandbox, "TARGET_X"):
            tx = sandbox.TARGET_X
            self.draw_line(tx, 0, tx, 8, COLOR_ENVIRONMENT, 3)

        if hasattr(sandbox, "BUILD_ZONE_X_MIN"):
            x_min = sandbox.BUILD_ZONE_X_MIN
            x_max = sandbox.BUILD_ZONE_X_MAX
            y_min = sandbox.BUILD_ZONE_Y_MIN
            y_max = sandbox.BUILD_ZONE_Y_MAX
            self.draw_line(x_min, y_min, x_max, y_min, COLOR_ENVIRONMENT, 1)
            self.draw_line(x_max, y_min, x_max, y_max, COLOR_ENVIRONMENT, 1)
            self.draw_line(x_max, y_max, x_min, y_max, COLOR_ENVIRONMENT, 1)
            self.draw_line(x_min, y_max, x_min, y_min, COLOR_ENVIRONMENT, 1)
