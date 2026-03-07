"""
K-02: The Climber task rendering module
Standardized for professional academic aesthetics.
"""
import sys
import os
import pygame
import math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from common.renderer import Renderer
from Box2D.b2 import dynamicBody, staticBody, revoluteJoint

# Standard Academic Palette
COLOR_BG = (0, 0, 0)
COLOR_ENV = (230, 194, 41)    # Goldenrod Yellow (#E6C229)
COLOR_AGENT = (76, 175, 80)  # Material Green (#4CAF50)
COLOR_TEMPLATE = (90, 90, 90)
COLOR_JOINT = (255, 220, 100)

RENDER_SCALE = 2.0  # Slightly zoomed out for panoramic view


class K02Renderer(Renderer):
    """K-02: The Climber — standardized 2D side-view mechanism."""

    def __init__(self, simulator):
        super().__init__(simulator)
        # Enforce 16:9 aspect ratio
        if simulator.can_display:
            target_h = 600
            target_w = int(target_h * 16 / 9)
            if simulator.screen_width != target_w or simulator.screen_height != target_h:
                simulator.screen_width = target_w
                simulator.screen_height = target_h
                simulator.screen = pygame.Surface((target_w, target_h))

    def world_to_screen(self, world_x, world_y):
        """Apply scale and camera offset."""
        ppm = self.simulator.ppm * RENDER_SCALE
        screen_x = world_x * ppm - self.camera_offset_x
        screen_y = self.simulator.screen_height - (world_y * ppm) - self.camera_offset_y
        return (int(screen_x), int(screen_y))

    def render(self, sandbox, agent_body, target_x, camera_offset_x):
        ppm = self.simulator.ppm
        sw = self.simulator.screen_width
        sh = self.simulator.screen_height
        
        if agent_body:
            # Focus on climber and its vertical progress
            center_world_x = 4.5
            center_world_y = agent_body.position.y
            cam_x = center_world_x * ppm * RENDER_SCALE - sw / 2
            cam_y = sh / 2 - center_world_y * ppm * RENDER_SCALE
            self.set_camera_offset(cam_x, cam_y)
        else:
            self.set_camera_offset(0, 0)
            
        self.clear(COLOR_BG)
        
        # Draw static terrain (wall and ground)
        for body in sandbox.world.bodies:
            if body.type == staticBody:
                self.draw_body(body,
                             dynamic_color=COLOR_AGENT,
                             static_color=COLOR_ENV,
                             outline_color=COLOR_ENV,
                             outline_width=2)
        
        # Draw dynamic objects (climber structure)
        for body in sandbox.world.bodies:
            if body.type == dynamicBody:
                is_template = False
                if hasattr(sandbox, '_climber_bodies'):
                    for key, value in sandbox._climber_bodies.items():
                        if 'template' in key and body == value:
                            is_template = True
                            break
                
                if is_template:
                    self.draw_body(body,
                                 dynamic_color=COLOR_TEMPLATE,
                                 static_color=COLOR_ENV,
                                 outline_color=COLOR_TEMPLATE,
                                 outline_width=1)
                else:
                    self.draw_body(body,
                                 dynamic_color=COLOR_AGENT,
                                 static_color=COLOR_ENV,
                                 outline_color=COLOR_AGENT,
                                 outline_width=2)
                    
                    # Optional: Draw leg axis if it's a leg (identified by shape or joints)
                    # For standardization, we'll keep it simple green solid bodies
        
        # Joints: one small marker per unique anchor
        if hasattr(sandbox, '_joints'):
            seen = set()
            for joint in sandbox._joints:
                if not isinstance(joint, revoluteJoint) or not joint.bodyA or not joint.bodyB:
                    continue
                try:
                    if hasattr(joint, 'localAnchorA'):
                        local_anchor = joint.localAnchorA
                    elif hasattr(joint, 'anchorA'):
                        local_anchor = joint.anchorA
                    else:
                        continue
                    world_anchor = joint.bodyA.GetWorldPoint(local_anchor)
                    key = (round(world_anchor.x, 3), round(world_anchor.y, 3))
                    if key in seen:
                        continue
                    seen.add(key)
                    anchor_screen = self.world_to_screen(world_anchor.x, world_anchor.y)
                    pygame.draw.circle(self.simulator.screen, COLOR_JOINT, anchor_screen, 4)
                except Exception:
                    pass

        # Target line (Goldenrod Yellow)
        if target_x and target_x > 0:
            wall_x = 5.0
            if hasattr(sandbox, '_wall_x'):
                wall_x = sandbox._wall_x
            self.draw_line(wall_x, target_x, wall_x + 3.0, target_x, COLOR_ENV, 3)
        
        # Build zone (Goldenrod Yellow)
        if hasattr(sandbox, 'BUILD_ZONE_X_MIN'):
            x_min = sandbox.BUILD_ZONE_X_MIN
            x_max = sandbox.BUILD_ZONE_X_MAX
            y_min = sandbox.BUILD_ZONE_Y_MIN
            y_max = sandbox.BUILD_ZONE_Y_MAX
            self.draw_line(x_min, y_min, x_max, y_min, COLOR_ENV, 1)
            self.draw_line(x_max, y_min, x_max, y_max, COLOR_ENV, 1)
            self.draw_line(x_max, y_max, x_min, y_max, COLOR_ENV, 1)
            self.draw_line(x_min, y_max, x_min, y_min, COLOR_ENV, 1)
