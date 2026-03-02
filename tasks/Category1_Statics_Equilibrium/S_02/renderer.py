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
        self.set_camera_offset(camera_offset_x)
        self.clear((30, 30, 30))
        
        # Draw foundation
        for body in sandbox.world.bodies:
            if body.type == staticBody:
                self.draw_body(body,
                             dynamic_color=(100, 150, 240),
                             static_color=(150, 100, 50),
                             outline_color=(200, 150, 100),
                             outline_width=2)
        
        # Draw structure
        for body in sandbox.world.bodies:
            if body.type == dynamicBody:
                self.draw_body(body,
                             dynamic_color=(100, 200, 100),
                             static_color=(150, 100, 50),
                             outline_color=(50, 150, 50),
                             outline_width=2)
        
        # Draw target height line
        if hasattr(sandbox, 'TARGET_HEIGHT'):
            self.draw_line(-10, sandbox.TARGET_HEIGHT, 10, sandbox.TARGET_HEIGHT, (255, 255, 0), 2)
