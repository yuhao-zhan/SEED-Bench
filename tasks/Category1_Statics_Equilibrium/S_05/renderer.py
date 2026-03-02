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
        self.set_camera_offset(camera_offset_x)
        self.clear((30, 30, 30))
        
        # Draw ground
        for body in sandbox.world.bodies:
            if body.type == staticBody:
                if "core" in str(body):
                    # Core - red
                    self.draw_body(body, static_color=(255, 0, 0), outline_color=(255, 100, 100), outline_width=3)
                else:
                    self.draw_body(body, static_color=(150, 100, 50), outline_color=(200, 150, 100), outline_width=2)
        
        # Draw meteors and structure
        for body in sandbox.world.bodies:
            if body.type == dynamicBody:
                # Check if it's a meteor (circle) or structure (polygon)
                is_meteor = False
                for fixture in body.fixtures:
                    if isinstance(fixture.shape, circleShape):
                        is_meteor = True
                        break
                
                if is_meteor:
                    self.draw_body(body, dynamic_color=(200, 100, 50), outline_color=(255, 150, 100), outline_width=2)
                else:
                    self.draw_body(body, dynamic_color=(100, 200, 100), outline_color=(50, 150, 50), outline_width=2)
