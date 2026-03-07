"""
S-06: The Overhang task rendering module
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody, kinematicBody


class S06Renderer(Renderer):
    """S-06: The Overhang task specific renderer"""
    
    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        """Render entire scene"""
        # Enforce 16:9 aspect ratio
        if self.simulator.screen_width != 800 or self.simulator.screen_height != 450:
            self.simulator.screen_width = 800
            self.simulator.screen_height = 450
            if self.simulator.can_display:
                import pygame
                self.simulator.screen = pygame.Surface((800, 450))
                
        # Panoramic Camera Viewport
        self.simulator.ppm = 35.0
        sw = self.simulator.screen_width
        sh = self.simulator.screen_height
        
        center_x_world = -2.5
        center_y_world = 1.0
        
        cam_x = center_x_world * self.simulator.ppm - sw / 2
        cam_y = sh / 2 - center_y_world * self.simulator.ppm
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
        
        # Draw target overhang line (Red)
        target_overhang = sandbox._terrain_config.get("target_overhang", 0.1)
        self.draw_line(target_overhang, -5, target_overhang, 15, RED, 2)
