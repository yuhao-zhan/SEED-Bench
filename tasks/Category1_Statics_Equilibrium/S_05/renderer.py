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
        
        # Access core from terrain_bodies
        core_body = sandbox._terrain_bodies.get("core")
        floor_body = sandbox._terrain_bodies.get("floor")
        
        # Draw all bodies
        for body in sandbox.world.bodies:
            if body == floor_body:
                self.draw_body(body, static_color=(150, 100, 50), outline_color=(200, 150, 100), outline_width=2)
            elif body == core_body:
                # Core - red
                self.draw_body(body, dynamic_color=(255, 0, 0), outline_color=(255, 100, 100), outline_width=3)
            elif body.type == dynamicBody:
                # Check if it's a meteor (part of sandbox._meteors)
                if body in sandbox._meteors:
                    self.draw_body(body, dynamic_color=(200, 100, 50), outline_color=(255, 150, 100), outline_width=2)
                else:
                    # Structure - green
                    self.draw_body(body, dynamic_color=(100, 200, 100), outline_color=(50, 150, 50), outline_width=2)
            else:
                # Other static bodies
                self.draw_body(body, static_color=(100, 100, 100), outline_color=(150, 150, 150), outline_width=1)
