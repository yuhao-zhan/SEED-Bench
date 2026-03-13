"""
S-05: The Shelter task rendering module
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody, circleShape


class S05Renderer(Renderer):
    """S-05: The Shelter task specific renderer"""
    
    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        """Render entire scene"""
        # Enforce 16:9 aspect ratio
        if self.simulator.screen_width != 800 or self.simulator.screen_height != 450:
            self.simulator.screen_width = 800
            self.simulator.screen_height = 450
            if self.simulator.can_display:
                import pygame
                self.simulator.screen = pygame.Surface((800, 450))
                
        # Panoramic Camera Viewport (center on core when available for mutated stages)
        self.simulator.ppm = 20.0
        sw = self.simulator.screen_width
        sh = self.simulator.screen_height
        
        center_x_world = getattr(sandbox, 'CORE_X', 10.0)
        center_y_world = max(getattr(sandbox, 'CORE_Y', 1.0) + 4.0, 6.0)  # above core, at least 6
        
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
            if hasattr(sandbox, '_meteors'):
                if body in sandbox._meteors:
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
