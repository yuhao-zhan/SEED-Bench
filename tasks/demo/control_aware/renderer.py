"""
Control-Aware task rendering module
Provides task-specific rendering logic with speed zone visualization
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class ControlAwareRenderer(Renderer):
    """Control-Aware task specific renderer with speed zone visualization"""
    
    def render(self, sandbox, agent_components, target_x, camera_offset_x):
        """
        Render entire scene with speed zone indicators
        Args:
            sandbox: DaVinciSandbox environment
            agent_components: Dictionary with 'slider'
            target_x: Target position
            camera_offset_x: Camera x offset
        """
        self.set_camera_offset(camera_offset_x)
        self.clear((30, 30, 30))  # Dark background
        
        # Draw speed zone indicators
        self._draw_speed_zones(sandbox, camera_offset_x)
        
        # Draw track
        for body in sandbox.world.bodies:
            if body.type == staticBody:
                # Track
                self.draw_body(body,
                             dynamic_color=(100, 150, 240),
                             static_color=(150, 150, 150),  # Gray track
                             outline_color=(200, 200, 200),
                             outline_width=2)
        
        # Draw slider
        if agent_components and 'slider' in agent_components:
            slider = agent_components['slider']
            if slider:
                self.draw_body(slider,
                             dynamic_color=(100, 200, 100),  # Green slider
                             static_color=(150, 100, 50),
                             outline_color=(50, 150, 50),
                             outline_width=2)
        
        # Draw target line
        target_screen_x = int((target_x * self.simulator.ppm) - camera_offset_x)
        if 0 <= target_screen_x <= self.simulator.screen_width:
            self.draw_line(target_x, 0, target_x, 10, (255, 0, 0), 3)
    
    def _draw_speed_zones(self, sandbox, camera_offset_x):
        """Draw speed zone indicators"""
        if hasattr(sandbox, 'get_speed_zone_limits'):
            zones = sandbox.get_speed_zone_limits()
            track_y = sandbox.TRACK_Y
            
            # Zone 1: 0-10m, limit 1.5 m/s (yellow - slow zone)
            zone1_start = zones["zone_1"]["start"]
            zone1_end = zones["zone_1"]["end"]
            self._draw_zone_overlay(zone1_start, zone1_end, track_y, (255, 200, 0, 50), "Zone 1: 1.5 m/s", camera_offset_x)
            
            # Zone 2: 10-20m, limit 3.0 m/s (green - fast zone)
            zone2_start = zones["zone_2"]["start"]
            zone2_end = zones["zone_2"]["end"]
            self._draw_zone_overlay(zone2_start, zone2_end, track_y, (0, 255, 0, 50), "Zone 2: 3.0 m/s", camera_offset_x)
            
            # Zone 3: 20-30m, limit 2.0 m/s (orange - medium zone)
            zone3_start = zones["zone_3"]["start"]
            zone3_end = zones["zone_3"]["end"]
            self._draw_zone_overlay(zone3_start, zone3_end, track_y, (255, 150, 0, 50), "Zone 3: 2.0 m/s", camera_offset_x)
    
    def _draw_zone_overlay(self, x_start, x_end, y, color, label, camera_offset_x):
        """Draw a zone overlay"""
        # Draw zone boundary lines
        self.draw_line(x_start, y - 0.5, x_start, y + 0.5, color[:3], 2)
        self.draw_line(x_end, y - 0.5, x_end, y + 0.5, color[:3], 2)
