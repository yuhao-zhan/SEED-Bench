"""
S-03: The Cantilever task rendering module
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody


class S03Renderer(Renderer):
    """S-03: The Cantilever task specific renderer. Camera centered on structure so the beam is in the middle of the frame."""

    # World position to put at screen center (structure horizontal center x=9, chord height y=1)
    CAMERA_CENTER_WORLD_X = 9.0
    CAMERA_CENTER_WORLD_Y = 1.0

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        """Render entire scene. Fix camera so structure (x=9, y=1) is at screen center."""
        ppm = self.simulator.ppm
        sw = self.simulator.screen_width
        sh = self.simulator.screen_height
        cam_x = self.CAMERA_CENTER_WORLD_X * ppm - sw / 2
        cam_y = sh / 2 - self.CAMERA_CENTER_WORLD_Y * ppm
        self.set_camera_offset(cam_x, cam_y)
        self.clear((30, 30, 30))
        
        # Draw wall and structure
        for body in sandbox.world.bodies:
            if body.type == staticBody:
                self.draw_body(body, static_color=(150, 100, 50), outline_color=(200, 150, 100), outline_width=2)
            elif body.type == dynamicBody:
                self.draw_body(body, dynamic_color=(100, 200, 100), outline_color=(50, 150, 50), outline_width=2)
        
        # Draw target reach line
        if hasattr(sandbox, 'TARGET_REACH'):
            self.draw_line(sandbox.TARGET_REACH, 0, sandbox.TARGET_REACH, 20, (255, 255, 0), 2)
