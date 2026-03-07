"""
S-02: The Skyscraper task rendering module
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class S02Renderer(Renderer):
    """S-02: The Skyscraper task specific renderer"""
    
    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        """Render entire scene"""
        # Enforce 16:9 aspect ratio
        if self.simulator.screen_width != 800 or self.simulator.screen_height != 450:
            self.simulator.screen_width = 800
            self.simulator.screen_height = 450
            if self.simulator.can_display:
                import pygame
                self.simulator.screen = pygame.Surface((800, 450))
                
        # Panoramic Camera Viewport for S-02 (Skyscraper)
        # Needs to cover height up to 35m and a reasonable width around x=0
        self.simulator.ppm = 10.0
        
        center_x_world = 0.0
        center_y_world = 17.5
        
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
                # Environment Base
                self.draw_body(body,
                             dynamic_color=ENV_COLOR,
                             static_color=ENV_COLOR,
                             outline_color=ENV_OUTLINE,
                             outline_width=2)
            else:
                # Agent-Created (Skyscraper)
                self.draw_body(body,
                             dynamic_color=AGENT_COLOR,
                             static_color=AGENT_COLOR,
                             outline_color=AGENT_OUTLINE,
                             outline_width=2)
        
        # Draw target height line (Red)
        if hasattr(sandbox, 'TARGET_HEIGHT'):
            self.draw_line(-20, sandbox.TARGET_HEIGHT, 20, sandbox.TARGET_HEIGHT, RED, 2)
