"""
K-04: The Pusher task rendering module
Provides task-specific rendering logic
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class K04Renderer(Renderer):
    """K-04: The Pusher task specific renderer"""
    
    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        self.set_camera_offset(camera_offset_x)
        self.clear((30, 30, 30))  # Dark background (match Category1_Statics_Equilibrium)
        
        # Draw static terrain (ground)
        for body in sandbox.world.bodies:
            if body.type == staticBody:
                # Ground - brown/rock (unified with Category1)
                self.draw_body(body,
                             dynamic_color=(100, 150, 240),
                             static_color=(150, 100, 50),
                             outline_color=(200, 150, 100),
                             outline_width=2)
        
        # Draw object to push
        if hasattr(sandbox, '_terrain_bodies') and "object" in sandbox._terrain_bodies:
            obj = sandbox._terrain_bodies["object"]
            # Object - distinct gray (heavy object, visible on dark)
            self.draw_body(obj,
                         dynamic_color=(180, 180, 180),
                         static_color=(150, 100, 50),
                         outline_color=(220, 220, 220),
                         outline_width=2)
        
        # Draw dynamic objects (pusher structure)
        for body in sandbox.world.bodies:
            if body.type == dynamicBody:
                # Check if it's template or actual pusher
                is_template = False
                if hasattr(sandbox, '_pusher_bodies'):
                    for key, value in sandbox._pusher_bodies.items():
                        if 'template' in key and body == value:
                            is_template = True
                            break
                
                # Check if it's the object
                is_object = False
                if hasattr(sandbox, '_terrain_bodies') and "object" in sandbox._terrain_bodies:
                    if body == sandbox._terrain_bodies["object"]:
                        is_object = True
                
                if is_object:
                    continue  # Already drawn above
                elif is_template:
                    # Template - faded on dark background
                    self.draw_body(body,
                                 dynamic_color=(90, 90, 90),
                                 static_color=(150, 100, 50),
                                 outline_color=(140, 140, 140),
                                 outline_width=1)
                else:
                    # Pusher structure - green (match Category1 bridge/links style)
                    self.draw_body(body,
                                 dynamic_color=(100, 200, 100),
                                 static_color=(150, 100, 50),
                                 outline_color=(50, 150, 50),
                                 outline_width=2)
        
        # Draw target line (red) if target_x is provided
        if target_x and target_x > 0:
            # Draw a red target line vertically at target position
            self.draw_line(target_x, 1.0, target_x, 8.0, (255, 0, 0), 3)
        
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
