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
        self.set_camera_offset(camera_offset_x)
        self.clear((30, 30, 30))  # Dark background
        
        # Draw static terrain (cliffs, water)
        for body in sandbox.world.bodies:
            if body.type == staticBody:
                # Check if it's water (sensor) or terrain
                is_water = False
                for fixture in body.fixtures:
                    if hasattr(fixture, 'isSensor') and fixture.isSensor:
                        is_water = True
                        break
                
                if is_water:
                    # Water - use blue
                    self.draw_body(body,
                                 dynamic_color=(100, 150, 240),
                                 static_color=(50, 100, 200),  # Blue water
                                 outline_color=(100, 150, 255),
                                 outline_width=2)
                else:
                    # Cliffs - use brown/rock color
                    self.draw_body(body,
                                 dynamic_color=(100, 150, 240),
                                 static_color=(150, 100, 50),  # Brown cliffs
                                 outline_color=(200, 150, 100),
                                 outline_width=2)
        
        # Draw dynamic objects (bridge structure and vehicle)
        for body in sandbox.world.bodies:
            if body.type == dynamicBody:
                # Check if it's vehicle or bridge structure
                is_vehicle = False
                if hasattr(sandbox, '_terrain_bodies'):
                    for key, value in sandbox._terrain_bodies.items():
                        if 'vehicle' in key and body == value:
                            is_vehicle = True
                            break
                
                if is_vehicle:
                    # Vehicle - use red
                    self.draw_body(body,
                                 dynamic_color=(255, 100, 100),  # Red vehicle
                                 static_color=(150, 100, 50),
                                 outline_color=(255, 150, 150),
                                 outline_width=3)
                else:
                    # Bridge structure - use green
                    self.draw_body(body,
                                 dynamic_color=(100, 200, 100),  # Green bridge
                                 static_color=(150, 100, 50),
                                 outline_color=(50, 150, 50),
                                 outline_width=2)
        
        # Draw target line (red)
        target_screen_x = int((target_x * self.simulator.ppm) - camera_offset_x)
        if 0 <= target_screen_x <= self.simulator.screen_width:
            # Draw a red target line from ground to top
            self.draw_line(target_x, 0, target_x, 20, (255, 0, 0), 3)
        
        # Draw build zone outline (yellow, semi-transparent)
        if hasattr(sandbox, 'BUILD_ZONE_X_MIN'):
            x_min = sandbox.BUILD_ZONE_X_MIN
            x_max = sandbox.BUILD_ZONE_X_MAX
            y_min = sandbox.BUILD_ZONE_Y_MIN
            y_max = sandbox.BUILD_ZONE_Y_MAX
            
            # Draw rectangle outline
            self.draw_line(x_min, y_min, x_max, y_min, (255, 255, 0), 1)
            self.draw_line(x_max, y_min, x_max, y_max, (255, 255, 0), 1)
            self.draw_line(x_max, y_max, x_min, y_max, (255, 255, 0), 1)
            self.draw_line(x_min, y_max, x_min, y_min, (255, 255, 0), 1)
