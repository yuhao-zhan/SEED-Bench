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
        self.set_camera_offset(camera_offset_x)
        self.clear((30, 30, 30))
        
        # Draw table (could be static or kinematic)
        for body in sandbox.world.bodies:
            if body == sandbox._terrain_bodies.get("table"):
                self.draw_body(body, static_color=(150, 100, 50), outline_color=(200, 150, 100), outline_width=2)
            elif body == sandbox._terrain_bodies.get("ceiling"):
                self.draw_body(body, static_color=(80, 80, 80), outline_color=(120, 120, 120), outline_width=2)
        
        # Draw blocks
        for body in sandbox.world.bodies:
            if body.type == dynamicBody:
                self.draw_body(body, dynamic_color=(100, 200, 100), outline_color=(50, 150, 50), outline_width=2)
        
        # Draw edge line (x=0)
        self.draw_line(0, -5, 0, 15, (255, 255, 0), 2)
        
        # Draw target overhang line
        target_overhang = sandbox._terrain_config.get("target_overhang", 0.1)
        self.draw_line(target_overhang, -5, target_overhang, 15, (255, 0, 0), 2)
