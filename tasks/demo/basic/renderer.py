"""
Basic task rendering module
Provides task-specific rendering logic
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class BasicRenderer(Renderer):
    """Basic task specific renderer"""
    
    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        """
        Render entire scene
        Args:
            sandbox: DaVinciSandbox environment
            agent_body: Agent main body (chassis)
            target_x: Target position
            camera_offset_x: Camera x offset
        """
        self.set_camera_offset(camera_offset_x)
        self.clear((30, 30, 30))  # Dark background
        
        # First draw all static objects (terrain, obstacles) - use more visible colors
        for body in sandbox.world.bodies:
            if body.type == staticBody:
                # Terrain and obstacles (use brighter colors, strong contrast with background)
                # Check if it's ground (y coordinate near 0) or obstacle
                if abs(body.position.y) < 1.0:
                    # Ground - use deep brown
                    self.draw_body(body,
                                 dynamic_color=(100, 150, 240),
                                 static_color=(150, 100, 50),    # Deep brown ground
                                 outline_color=(200, 150, 100), # Light brown outline
                                 outline_width=2)
                else:
                    # Obstacles - use vibrant orange, very visible
                    self.draw_body(body,
                                 dynamic_color=(100, 150, 240),
                                 static_color=(255, 140, 0),     # Vibrant orange obstacles
                                 outline_color=(255, 200, 0),   # Bright yellow outline
                                 outline_width=4)                # Very thick outline, ensure visibility
        
        # Then draw all dynamic objects (Agent components)
        for body in sandbox.world.bodies:
            if body.type == dynamicBody:
                # Determine if it's a wheel or chassis
                is_wheel = False
                for fixture in body.fixtures:
                    from Box2D.b2 import circleShape
                    if isinstance(fixture.shape, circleShape):
                        is_wheel = True
                        break
                
                if is_wheel:
                    # Wheel (green, consistent with original code)
                    self.draw_body(body,
                                 dynamic_color=(100, 200, 100),  # Green wheel
                                 static_color=(150, 100, 50),
                                 outline_color=(50, 150, 50),    # Dark green outline
                                 outline_width=2)
                else:
                    # Chassis (blue, more visible)
                    self.draw_body(body,
                                 dynamic_color=(80, 130, 255),   # Brighter blue chassis
                                 static_color=(150, 100, 50),
                                 outline_color=(200, 200, 255),  # Light blue outline
                                 outline_width=3)                 # Thicker outline, ensure visibility
        
        # Draw target line (red, more visible)
        target_screen_x = int((target_x * self.simulator.ppm) - camera_offset_x)
        if 0 <= target_screen_x <= self.simulator.screen_width:
            # Draw a red target line from ground to top
            self.draw_line(target_x, 0, target_x, 15, (255, 0, 0), 3)
