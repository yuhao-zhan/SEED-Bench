"""
S-01: The Bridge task rendering module
Provides task-specific rendering logic
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class S01Renderer(Renderer):
    """S-01: The Bridge task specific renderer"""
    
    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        # Enforce 16:9 aspect ratio
        if self.simulator.screen_width != 800 or self.simulator.screen_height != 450:
            self.simulator.screen_width = 800
            self.simulator.screen_height = 450
            if self.simulator.can_display:
                import pygame
                # Recreate surface to match new dimensions
                self.simulator.screen = pygame.Surface((800, 450))
                
        # Panoramic Camera Viewport for S-01 (Bridge)
        # We need to cover x from 0 to 45 (to see both cliffs and target at x=30+)
        # And y from 0 to 20
        # For a width of 45m across 800 pixels, ppm should be around 800/45 ~ 17.7
        self.simulator.ppm = 15.0
        
        # Center the camera
        # Let's say we want x=20 to be the center of the screen
        center_x_world = 20.0
        center_y_world = 10.0
        
        cam_x = center_x_world * self.simulator.ppm - self.simulator.screen_width / 2
        cam_y = self.simulator.screen_height / 2 - center_y_world * self.simulator.ppm
        
        self.set_camera_offset(cam_x, cam_y)
        self.clear((0, 0, 0))  # Pure Black background
        
        # Updated Academic Color palette
        ENV_COLOR = (230, 194, 41)       # #E6C229 (Goldenrod Yellow)
        ENV_OUTLINE = (180, 144, 0)      # Darker Goldenrod
        AGENT_COLOR = (76, 175, 80)      # #4CAF50 (Material Green)
        AGENT_OUTLINE = (26, 125, 30)    # Darker Green
        RED = (255, 0, 0)
        
        # Draw all bodies
        for body in sandbox.world.bodies:
            # Determine if it's environment or agent-created
            is_environment = False
            if hasattr(sandbox, '_terrain_bodies'):
                if body in sandbox._terrain_bodies.values():
                    is_environment = True
            
            if is_environment:
                self.draw_body(body,
                             dynamic_color=ENV_COLOR,
                             static_color=ENV_COLOR,
                             outline_color=ENV_OUTLINE,
                             outline_width=2)
            else:
                self.draw_body(body,
                             dynamic_color=AGENT_COLOR,
                             static_color=AGENT_COLOR,
                             outline_color=AGENT_OUTLINE,
                             outline_width=2)
        
        # Draw target line (red)
        self.draw_line(target_x, 0, target_x, 20, RED, 3)
        
        # Draw build zone outline
        if hasattr(sandbox, 'BUILD_ZONE_X_MIN'):
            x_min = sandbox.BUILD_ZONE_X_MIN
            x_max = sandbox.BUILD_ZONE_X_MAX
            y_min = sandbox.BUILD_ZONE_Y_MIN
            y_max = sandbox.BUILD_ZONE_Y_MAX
            
            # Draw rectangle outline
            self.draw_line(x_min, y_min, x_max, y_min, ENV_COLOR, 1)
            self.draw_line(x_max, y_min, x_max, y_max, ENV_COLOR, 1)
            self.draw_line(x_max, y_max, x_min, y_max, ENV_COLOR, 1)
            self.draw_line(x_min, y_max, x_min, y_min, ENV_COLOR, 1)
