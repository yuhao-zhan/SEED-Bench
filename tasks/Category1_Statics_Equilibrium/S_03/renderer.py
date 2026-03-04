"""
S-03: The Cantilever task rendering module
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class S03Renderer(Renderer):
    """S-03: The Cantilever task specific renderer."""

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        """Render entire scene. Adjust camera to see the full structure."""
        ppm = self.simulator.ppm
        sw = self.simulator.screen_width
        sh = self.simulator.screen_height
        
        # Determine structure bounds to center camera
        min_x, max_x = 0, 12
        min_y, max_y = 0, 10
        
        bodies = list(sandbox.world.bodies)
        if bodies:
            xs = [b.position.x for b in bodies]
            ys = [b.position.y for b in bodies]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        
        # Increase ppm if the structure is very large? 
        # Actually Renderer usually handles ppm. Let's just adjust camera.
        
        cam_x = center_x * ppm - sw / 2
        cam_y = sh / 2 - center_y * ppm
        self.set_camera_offset(cam_x, cam_y)
        self.clear((20, 20, 20))
        
        # Draw wall and structure
        for body in sandbox.world.bodies:
            color = (100, 100, 100) # static
            if body.type == dynamicBody:
                if body in getattr(sandbox, '_load_bodies', []):
                    color = (255, 50, 50) # loads
                else:
                    color = (100, 200, 100) # structure
            else:
                color = (150, 100, 50) # wall
                
            self.draw_body(body, dynamic_color=color, static_color=color, outline_color=(200, 200, 200), outline_width=1)
        
        # Draw target reach line
        target_reach = sandbox._terrain_config.get("target_reach", 12.0)
        self.draw_line(target_reach, -20, target_reach, 30, (255, 255, 0), 2)
